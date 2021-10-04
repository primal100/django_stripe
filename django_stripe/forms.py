from django import forms
import pycountry


class BillingDetailsForm(forms.Form):
    country = forms.ChoiceField(choices=[
        (country.alpha_2, country.name) for country in pycountry.countries
    ], required=True)
    address_line_1 = forms.CharField(max_length=120, required=True)
    address_line_2 = forms.CharField(max_length=120, required=False)
    city = forms.CharField(max_length=85, required=True)
    state = forms.CharField(max_length=85, required=True)
    postcode = forms.CharField(max_length=10, required=False)
    phone = forms.CharField(max_length=15, required=False)
