app_name = "lms_lock_chapter"
app_title = "LMS Lock Chapter"
app_publisher = "GL Soltec"
app_description = "Bloquear Capitulos"
app_email = "suporte@glsoltec.com.br"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "lms_lock",
# 		"logo": "/assets/lms_lock_chapter/logo.png",
# 		"title": "Lms Lock",
# 		"route": "/lms_lock",
# 		"has_permission": "lms_lock_chapter.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/lms_lock_chapter/css/lms_lock.css"
# app_include_js = "/assets/lms_lock_chapter/js/lms_lock.js"

# include js, css files in header of web template
# web_include_css = "/assets/lms_lock_chapter/css/lms_lock.css"
# web_include_js = "/assets/lms_lock_chapter/js/lms_lock.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "lms_lock/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "lms_lock/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "lms_lock_chapter.utils.jinja_methods",
# 	"filters": "lms_lock_chapter.utils.jinja_filters"
# }

# Installation
# ------------

before_install = "lms_lock_chapter.install.before_install"
after_install = "lms_lock_chapter.install.after_install"

# Uninstallation
# ------------

before_uninstall = "lms_lock_chapter.uninstall.before_uninstall"
after_uninstall = "lms_lock_chapter.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "lms_lock_chapter.utils.before_app_install"
# after_app_install = "lms_lock_chapter.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "lms_lock_chapter.utils.before_app_uninstall"
# after_app_uninstall = "lms_lock_chapter.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "lms_lock_chapter.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "lms_lock_chapter.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"lms_lock_chapter.tasks.all"
# 	],
# 	"daily": [
# 		"lms_lock_chapter.tasks.daily"
# 	],
# 	"hourly": [
# 		"lms_lock_chapter.tasks.hourly"
# 	],
# 	"weekly": [
# 		"lms_lock_chapter.tasks.weekly"
# 	],
# 	"monthly": [
# 		"lms_lock_chapter.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "lms_lock_chapter.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "lms_lock_chapter.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "lms_lock_chapter.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "lms_lock_chapter.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["lms_lock_chapter.utils.before_request"]
# after_request = ["lms_lock_chapter.utils.after_request"]

# Job Events
# ----------
# before_job = ["lms_lock_chapter.utils.before_job"]
# after_job = ["lms_lock_chapter.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"lms_lock_chapter.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

override_doctype_class = {
    "LMS Course": "lms_lock_chapter.lms_overrides.LMSCourseLMSLock"
}

doctype_js = {"LMS Course": "public/js/lms_chapter_lock.js"}

web_include_js = ["/assets/lms_lock_chapter/js/lms_portal_lock.js"]

has_permission = {
    "Course Lesson": "lms_lock_chapter.lms_overrides.check_lesson_permission",
    "Course Chapter": "lms_lock_chapter.lms_overrides.check_chapter_permission_hook"
}

after_request = ["lms_lock_chapter.lms_overrides.inject_portal_script"]

doc_events = {
    "LMS Course Progress": {
        "after_insert": "lms_lock_chapter.lms_overrides.invalidate_chapter_completion_cache",
        "on_update": "lms_lock_chapter.lms_overrides.invalidate_chapter_completion_cache",
    }
}