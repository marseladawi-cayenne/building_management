# Copyright (c) 2024, Cayenne Systems and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class BuildingMember(Document):
	def validate(self):
		duplicate = frappe.db.exists(self.doctype, {'user':self.user,'building':self.building})
		
		if duplicate and duplicate != self.name:
			frappe.throw("Member already exists in this building")