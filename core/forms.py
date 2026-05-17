from django import forms


class SystemDataImportForm(forms.Form):
    backup_file = forms.FileField(
        label="Backup file",
        help_text="Upload a ZIP backup exported from this page.",
    )
    confirm_replace = forms.BooleanField(
        label="I understand this will replace current system data",
        required=True,
        help_text="All Django model-backed data in the backup will replace the current database rows.",
    )
