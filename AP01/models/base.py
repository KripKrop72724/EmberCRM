from django.db import models

from AP01.models.core import User, T01Div10
from AP01.models.functional import LeadInteraction


class T01Nat10(models.Model):
    nationality = models.CharField(db_column="sNatEng", max_length=50)

    class Meta:
        db_table = "T01NAT10"
        ordering = ["nationality"]
        verbose_name = "a7.Nationality Master"

    def __str__(self) -> str:
        return self.nationality


class T01Slm10(models.Model):
    first_name = models.CharField(db_column="sFrstNm", max_length=255)
    last_name = models.CharField(
        db_column="sLstNm", max_length=255, blank=True, null=True
    )
    mobile = models.CharField(db_column="sMobile", max_length=30, blank=True, null=True)
    telephone = models.CharField(
        db_column="stelephn", max_length=30, blank=True, null=True
    )
    email = models.EmailField(db_column="eEmail", max_length=255)
    commission_percent = models.DecimalField(
        max_digits=6, decimal_places=2, db_column="fCommPer", default=0.00, blank=True, null=True
    )
    GENDER_CHOICE = (("male", "Male"), ("female", "Female"), ("other", "Other"))
    gender = models.CharField(db_column="sGender", max_length=25, choices=GENDER_CHOICE, blank=True,)
    nationality = models.ForeignKey(
        T01Nat10, models.PROTECT, db_column="snatnality", max_length=40, blank=True, null=True
    )
    profile_pic = models.ImageField(
        upload_to='profile_pics/', blank=True, null=True, db_column='bPic'
    )
    user = models.ForeignKey(
        User, models.CASCADE, db_column="IdUsr", null=True
    )
    division = models.ForeignKey(
        T01Div10, models.PROTECT, db_column="div", default=1)

    was_attached = models.BooleanField(default=False, null=True, blank=True, db_column="was_attached")

    add_to_rotation = models.BooleanField(default=True, db_column="add_to_rotation")

    class Meta:
        db_table = "T01SLM10"
        verbose_name = "a6.Sales Person"

    def __str__(self):
        return f"{self.first_name} - {self.last_name}"

    def total_lead_clicks(self):
        # This will return the total number of clicks by this salesperson across all leads.
        return LeadInteraction.objects.filter(interacted_by=self).count()

    def total_clicks_for_lead(self, lead):
        # This will return the total number of clicks by this salesperson for a specific lead.
        return LeadInteraction.objects.filter(interacted_by=self, lead=lead).count()


class T01Tl10(models.Model):
    first_name = models.CharField(db_column="sFrstNm", max_length=255)
    last_name = models.CharField(
        db_column="sLstNm", max_length=255, blank=True, null=True
    )
    mobile = models.CharField(db_column="sMobile", max_length=30, blank=True, null=True)
    telephone = models.CharField(
        db_column="stelephn", max_length=30, blank=True, null=True
    )
    email = models.EmailField(db_column="eEmail", max_length=255)
    commission_percent = models.DecimalField(
        max_digits=6, decimal_places=2, db_column="fCommPer", default=0.00, null=True, blank=True,
    )
    GENDER_CHOICE = (("male", "Male"), ("female", "Female"))
    gender = models.CharField(db_column="sGender", max_length=25, choices=GENDER_CHOICE)
    nationality = models.ForeignKey(
        T01Nat10, models.PROTECT, db_column="snatnality", max_length=40
    )
    profile_pic = models.ImageField(
        upload_to='profile_pics/', blank=True, null=True, db_column='bPic'
    )
    user_id = models.ForeignKey(
        User, models.CASCADE, db_column="IdUsr", null=True
    )
    division = models.ForeignKey(
        T01Div10, models.PROTECT, db_column="div", default=1)

    sales_persons = models.ManyToManyField(T01Slm10, db_table="T01Slm10_T01Tl10", blank=True)

    class Meta:
        db_table = "T01TL10"
        verbose_name = "a6.Sales Person"

    def __str__(self):
        return f"{self.first_name} - {self.last_name}"


class T01Lan10(models.Model):
    language_name = models.CharField(db_column="sLanguage", max_length=40)

    class Meta:
        db_table = "T01LAN10"
        verbose_name = "a9.Language"

    def __str__(self) -> str:
        return self.language_name


# Sales Person Skill
class T01Slm11(models.Model):
    sales_person = models.ForeignKey(
        T01Slm10, models.CASCADE, db_column="IdSlm", null=True
    )
    language = models.ForeignKey(
        T01Lan10, models.CASCADE, db_column="IdLan", null=True, blank=True
    )
    read = models.BooleanField(db_column="bRead", default=False)
    write = models.BooleanField(db_column="bWrite", default=False)
    speak = models.BooleanField(db_column="bSpeak", default=False)

    class Meta:
        db_table = "T01SLM11"
        verbose_name = "Sales Person Skill"


# Team lead Skill
class T01Slm11T(models.Model):
    team_lead = models.ForeignKey(
        T01Tl10, models.CASCADE, db_column="IdSlm", null=True, related_name='skills'
    )
    language = models.ForeignKey(
        T01Lan10, models.CASCADE, db_column="IdLan", null=True, blank=True
    )
    read = models.BooleanField(db_column="bRead", default=False)
    write = models.BooleanField(db_column="bWrite", default=False)
    speak = models.BooleanField(db_column="bSpeak", default=False)

    class Meta:
        db_table = "T01SLM11T"
        verbose_name = "Team Lead Person Skill"
