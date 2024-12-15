# Copyright (c) 2024, Cayenne Systems and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe

class BuildingExpense(Document):
	def validate(self):
		expense_amount = self.amount
		total = 0
		for payment in self.payments:
			journal_entry_doc = frappe.get_doc("Journal Entry", payment.entry)
			total += journal_entry_doc.total_debit
		
		if total > expense_amount:
			frappe.throw("Total paymnts cannot exceed expense amount")

		self.paid_amount = total

		if total == expense_amount and self.status != "Cancelled":
			self.status = "Paid"
		