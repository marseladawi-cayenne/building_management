import frappe

def building_on_create(doc,method=None):
    company_doc = frappe.new_doc("Company")
    company_doc.company_name = doc.building_name
    company_doc.country = "Palestinian Territory, Occupied"
    company_doc.default_currency = "ILS"
    company_doc.abbreviate()
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