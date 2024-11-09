app_name = "building_management"
app_title = "Building Management"
app_publisher = "Cayenne Systems"
app_description = "Building Management Module"
app_email = "info@cayenne-systems.com"
app_license = "mit"


doc_events = {
    "Building": {
        "after_insert": "building_management.api.building_on_create"
    },
    "Building Member": {
        "after_insert": "building_management.api.building_member_on_create"
    }
}