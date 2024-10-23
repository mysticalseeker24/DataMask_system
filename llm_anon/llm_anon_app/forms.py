from django import forms
from crispy_bootstrap5.bootstrap5 import FloatingField

class InitialInputForm(forms.Form):
    input_text = forms.CharField(
        label="",
        widget=forms.Textarea(attrs={"rows": 6, "cols": 40}),
    )
    use_case = forms.CharField(
        widget=forms.HiddenInput(),
        initial=""
    )