FORM_CONTROL_CLASS = "block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
FORM_CHECKBOX_CLASS = (
    "h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-600"
)

TEXT_INPUT_ATTRS = {"class": FORM_CONTROL_CLASS}
DATE_INPUT_ATTRS = {"class": FORM_CONTROL_CLASS, "type": "date"}
NUMBER_INPUT_ATTRS = {"class": FORM_CONTROL_CLASS}
SELECT_ATTRS = {"class": FORM_CONTROL_CLASS}
TEXTAREA_ATTRS = {"class": FORM_CONTROL_CLASS, "rows": 3}
CHECKBOX_ATTRS = {"class": FORM_CHECKBOX_CLASS}
