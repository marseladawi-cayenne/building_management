import frappe
from datetime import datetime
from frappe.desk.query_report import run
from frappe.exceptions import ValidationError

def building_on_create(doc,method=None):
    company_doc = frappe.new_doc("Company")
    company_doc.company_name = doc.building_name
    company_doc.country = "Palestinian Territory, Occupied"
    company_doc.default_currency = "ILS"
    company_doc.abbreviate()
    company_doc.save(ignore_permissions=True)
    company_doc = frappe.get_doc("Company", company_doc.name)
    pending_cash = frappe.new_doc("Account")
    pending_cash.account_name = "Pending Cash"
    pending_cash.company = company_doc.name
    pending_cash.parent_account = f"Cash In Hand - {company_doc.abbr}"
    pending_cash.currency = "ILS"
    pending_cash.save()
    company_doc.default_deferred_revenue_account = f"Pending Cash - {company_doc.abbr}"
    company_doc.default_deferred_expense_account = f"Utility Expenses - {company_doc.abbr}"
    company_doc.save(ignore_permissions=True)
    doc.company = company_doc.name
    doc.save()
    
def building_member_on_create(doc ,method=None):
    customer_doc = frappe.new_doc("Customer")
    customer_doc.customer_name = f"{doc.building}-{doc.user}"
    customer_doc.save()
    doc.customer = customer_doc.name
    doc.save()
    user_permission = frappe.new_doc("User Permission")
    user_permission.user = doc.user
    user_permission.allow = "Company"
    user_permission.for_value = doc.building
    user_permission.save()
    

@frappe.whitelist()
def monthly_subscription():
    companies = frappe.get_list("Company",fields=['name','abbr'])
    for company in companies:
        if len(frappe.get_list("Building", filters={'name': company['name']})) > 0:
            building_members = frappe.get_list("Building Member", filters={'building': company['name']}, fields=['monthly_subscription','customer'])
            total_subscriptions = sum(member['monthly_subscription'] for member in building_members)
            if total_subscriptions > 0:
                journal_e = frappe.new_doc("Journal Entry")
                journal_e.company = company['name']
                journal_e.posting_date = datetime.now()
                journal_e.user_remark = "Monthly Subscription"
                journal_e.append('accounts', {'account': f"Pending Cash - {company['abbr']}",'debit_in_account_currency': total_subscriptions})
                for member in building_members:
                        journal_e.append('accounts', {'account': f"Debtors - {company['abbr']}",'party_type': 'Customer','party': member['customer'] ,'credit_in_account_currency': member['monthly_subscription']})
                
                journal_e.submit()
 
@frappe.whitelist()
def get_building_member_account(company=None):
    data = {}
    data['metadata'] = frappe.get_meta("Building Member").fields
    data['metadata'].append({'fieldname': 'outstanding_balance','label':'Outstanding Balance','fieldtype':'Float'})
    data['metadata'].append({'fieldname': 'user_full_name','label':'user_full_name','fieldtype':'Data'})
    if company != None:
        date = datetime.now().date().strftime('%Y-%m-%d')
        member_list = {member['customer']: member for member in frappe.get_all("Building Member", filters={'building': company}, fields='*')}
        report = run(report_name='Accounts Receivable Summary',filters={"company":company,"report_date":date,"ageing_based_on":"Due Date","range1":30,"range2":60,"range3":90,"range4":120,"party":[]})
        for row in report['result']:
            if type(row) == frappe._dict:
                if row['party'] in member_list.keys():
                    print(member_list[row['party']])
                    user_doc = frappe.get_doc("User", member_list[row['party']]['user'])
                    member_list[row['party']]['user_full_name'] = user_doc.full_name
                    member_list[row['party']]['outstanding_balance'] = row['outstanding'] * -1
        data['data'] = member_list

    return data


@frappe.whitelist()
def custom_building_action(building_id,action):
    user = frappe.session.user

    if frappe.db.exists("Building Member", {"building": building_id, "user": user}):
        if frappe.has_permission("Building", "building_manager", user=user):
            return {"status": "success", "message": "Action completed with elevated permissions"}
        else:
            frappe.throw("You do not have sufficient permissions.")
    else:
        frappe.throw("User is not a member of this building.")
        
@frappe.whitelist()
def create_building_expense(building, doctype, description, amount):
    amount = int(amount)
    company = frappe.get_doc("Company", building)
    
    expense_doc = frappe.new_doc(doctype)
    expense_doc.building = building
    expense_doc.description = description
    expense_doc.amount = amount
    
    journal_e = frappe.new_doc("Journal Entry")
    journal_e.company = building
    journal_e.posting_date = datetime.now()
    journal_e.append('accounts', {'account': f"Utility Expenses - {company.abbr}",'debit_in_account_currency': amount})
    journal_e.append('accounts', {'account': f"Cash - {company.abbr}",'credit_in_account_currency': amount})
                
    journal_e.save()
    journal_e.submit()
    
    expense_doc.append('payments', {'entry':journal_e})            
    
    expense_doc.save()
    
@frappe.whitelist()
def cancel_expense(expense):
    expense_doc = frappe.get_doc("Building Expense", expense)
    for payment in expense_doc.payments:
        journal_e = frappe.get_doc("Journal Entry", payment.entry)
        journal_e.cancel()
        
    expense_doc.status = "Cancelled"
    expense_doc.save()
    
    
    
class UserExistsInBuilding(Exception):
    pass

@frappe.whitelist()
def add_building_member(user, building):
    """
    Adds a user to a building as a Building Member.

    Args:
        user (dict): User object containing at least 'email' and optionally other fields.
        building (str): Name or ID of the building.

    Raises:
        UserExistsInBuilding: If the user already exists as a member of the building.
    """
    # Ensure user email is provided
    user_email = user.get("email")
    if not user_email:
        frappe.throw("User email is required.")

    # Check if user exists
    existing_user = frappe.db.get_value("User", {"email": user_email}, "name")
    
    if not existing_user:
        # Create the user if not found
        new_user = frappe.get_doc({
            "doctype": "User",
            "email": user_email,
            "first_name": user.get("first_name", user_email.split("@")[0]),  # Use provided first_name or email prefix
            "last_name": user.get("last_name", ""),  # Use provided last_name or empty
            "enabled": 1
        })
        new_user.insert()
        frappe.db.commit()  # Save the new User
        existing_user = new_user.name  # Get the name of the newly created user

    # Check if Building Member already exists for the user and building
    existing_member = frappe.db.exists(
        "Building Member", 
        {"user": existing_user, "building": building}
    )

    if existing_member:
        raise UserExistsInBuilding(f"User {user_email} is already a member of building {building}.")
    
    # Create a new Building Member
    building_member = frappe.get_doc({
        "doctype": "Building Member",
        "user": existing_user,
        "building": building
    })
    building_member.insert()
    frappe.db.commit()  # Save the Building Member

    return {"status": "success", "message": building_member}