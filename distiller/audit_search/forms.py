"""
Audit search form and related code.

@todo soon enough: Separate this into its own tiny extension/module so you can
import it both here and in the file that's actually doing the filtering.
"""

from datetime import datetime

from django import forms
from django.utils.safestring import mark_safe

from distiller.data import constants
from distiller.data.etls.load_dumps import FAC_START_YEAR
from distiller.data.models import AssistanceListing


# This is a dictionary of agencies indexed by their two-digit Federal Agency
# Prefixes, as specified on the Federal Audit Clearinghouse.
#
# The prefixes must be strings. Otherwise we'll lose the leading zeroes.
# Since Python 3.6, dictionaries are OrderedDicts by default, so we don't need
# to do anything special to keep the agency names in alphabetical order.
#
# Since agencies may share a prefix, don't store this as a dictionary.
#
AGENCY_CHOICES = (
    ('', ''),
) + constants.AGENCIES


class AgencySelectionForm(forms.Form):
    agency = forms.ChoiceField(
        choices=AGENCY_CHOICES,
        label_suffix=None,
        label=mark_safe(
            'Parent agency <span class="required">(required)</span>:'
        ),
    )
    sub_agency = forms.ChoiceField(required=False)
    audit_year = forms.ChoiceField(
        choices=lambda: (('', ''),) + tuple(
            (year, year)
            for year in range(datetime.now().year, FAC_START_YEAR, -1)
        ),
        required=False
    )
    start_date = forms.DateField(
        required=False,
        label='Audit accepted date - From'
    )
    end_date = forms.DateField(
        required=False,
        label='Audit accepted date - To'
    )
    page = forms.IntegerField(initial=1, required=False)
    findings = forms.BooleanField(
        required=False,
        initial=True,
        label='Only show audits with findings',
        label_suffix="",
    )
    # Used when drilling-down search terms
    filtering = forms.IntegerField(required=False)

    agency_cog_oversight = forms.BooleanField(
        required=False,
        initial=False,
        label='Include audits where parent agency is cognizant/oversight',
    )
    sort = forms.ChoiceField(
        required=False,
        choices=(
            ('auditee_name', 'auditee_name'),
            ('fy_end_date', 'fy_end_date'),
            ('fac_accepted_date', 'fac_accepted_date'),
            ('cog_over', 'cog_over'),
            ('material_weakness', 'material_weakness'),
            ('qcosts', 'qcosts'),
            ('num_findings', 'num_findings'),
        )
    )
    order = forms.ChoiceField(
        required=False,
        choices=(
            ('asc', 'asc'),
            ('desc', 'desc'),
        )
    )
    fmt = forms.ChoiceField(
        initial='html',
        choices=(
            ('html', 'hmtl'),
            ('csv', 'csv'),
        )
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['start_date'].widget.attrs['placeholder'] = 'mm/dd/yyyy'
        self.fields['end_date'].widget.attrs['placeholder'] = 'mm/dd/yyyy'

        # Support filtering on subagency, default to first choice
        agency = self['agency'].value() or AGENCY_CHOICES[0][0]
        self.fields['sub_agency'].choices = [
            (None, '')  # all sub-agencies under this prefix
        ] + [
            (sub, sub)
            for sub in AssistanceListing.objects.distinct_agencies(agency)
        ]

        # If the only choice is "all", make this field disabled.
        if len(self.fields['sub_agency'].choices) == 1:
            self.fields['sub_agency'].widget.attrs['disabled'] = True

    def clean_sub_agency(self):
        return self.cleaned_data['sub_agency'] or None

    def clean_audit_year(self):
        return self.cleaned_data['audit_year'] or None

    def clean_filtering(self):
        if self.cleaned_data['filtering']:
            raise forms.ValidationError('Cannot search when filtering')
        return self.cleaned_data['filtering']

    def clean_end_date(self):
        if self.cleaned_data.get('start_date') and (
            self.cleaned_data['end_date'] < self.cleaned_data['start_date']
        ):
            raise forms.ValidationError(
                'End date may not be earlier than start date'
            )

        return self.cleaned_data['end_date']

    def clean_start_date(self):
        if self.cleaned_data.get('end_date') and (
            self.cleaned_data['start_date'] < self.cleaned_data['end_date']
        ):
            raise forms.ValidationError(
                'Start date may not be earlier than start date'
            )

        return self.cleaned_data['start_date']
