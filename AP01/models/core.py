from django.contrib.auth.models import AbstractUser, Group
from django.db import models
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel
from simple_history.models import HistoricalRecords


class User(AbstractUser):
    email = models.EmailField(unique=False)
    otp = models.CharField(db_column="cotp", max_length=6, blank=True, null=True)
    phone_number = models.CharField(
        db_column="cphone", max_length=12, unique=True, null=True
    )
    otp_expire_at = models.DateTimeField(db_column="dexpire", blank=True, null=True)
    stripe_customer_id = models.CharField(max_length=50, blank=True, null=True)
    history = HistoricalRecords()

    class Meta(AbstractUser.Meta):
        ordering = ("username",)


class T01Pkg10(models.Model):
    name = models.CharField(max_length=60, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    hide_phone_numbers = models.BooleanField(default=False)
    hide_comments = models.BooleanField(default=True)
    history = HistoricalRecords()

    def __str__(self):
        return self.name


class T01Com10(MPTTModel):
    users = models.ManyToManyField(User, blank=True, related_name="companies")

    parent = TreeForeignKey(
        "self", models.PROTECT, db_column="IDParentCo", blank=True, null=True
    )
    packages = models.ManyToManyField(T01Pkg10, blank=True)
    company_name = models.CharField(db_column="sCompName", max_length=60)
    company_address = models.CharField(db_column="sCompAddr", max_length=60, blank=True)
    company_location = models.CharField(
        db_column="sCompLocation", max_length=60, blank=True
    )
    logo_file_link = models.FileField(
        upload_to="images/logos/", null=True, blank=True, default=None
    )
    document_header = models.CharField(
        db_column="sCompHeader", max_length=50, blank=True
    )
    document_footer = models.CharField(
        db_column="sCompFooter", max_length=50, blank=True
    )
    active_status = models.BooleanField(db_column="bCompStatus", default=True)
    stripe_id = models.CharField(
        db_column="stripe_id", max_length=50, blank=True, editable=False
    )
    history = HistoricalRecords()

    class Meta:
        db_table = "T01COM10"
        verbose_name = "a1.Company Master"

    class MPTTMeta:
        order_insertion_by = ["company_name"]

    def __str__(self):
        return self.company_name


class CompanyGroup(models.Model):
    company = models.ForeignKey(T01Com10, on_delete=models.CASCADE, null=True, blank=True)
    group = models.OneToOneField(Group, on_delete=models.CASCADE)
    history = HistoricalRecords()


class T01Cfg10(models.Model):
    license_name = models.CharField(
        db_column="sLicName", max_length=30, default="Demo Company"
    )
    software_name = models.CharField(
        db_column="sSoftwareName", max_length=10, default="ebos22"
    )
    num_of_users = models.IntegerField(db_column="nLicUsers", blank=True, null=True)
    date_issued = models.DateField(db_column="dLicIssued", null=True)
    date_expiry = models.DateField(db_column="dLicExpiry", null=True)
    email_sender = models.EmailField(db_column="eEmail", max_length=100, null=True)
    password_sender = models.CharField(db_column="cpassword", max_length=100, null=True)
    history = HistoricalRecords()

    class Meta:
        db_table = "T01CFG10"
        verbose_name = "e1.Configuration"

    def __str__(self):
        return self.license_name


class T01Div10(models.Model):
    company = models.ForeignKey(
        T01Com10, models.PROTECT, db_column="IDComDiv", null=True
    )
    division_name = models.CharField(db_column="sBuName", max_length=60)
    division_addr = models.CharField(db_column="BuAddress", max_length=60, blank=True)
    division_location = models.CharField(
        db_column="BuLocation", max_length=50, blank=True
    )
    user = models.ManyToManyField(
        User, db_column="IDUsers", blank=True, related_name="users"
    )
    hide_header = models.BooleanField(null=True, blank=True, default=False)
    history = HistoricalRecords()

    class Meta:
        db_table = "T01DIV10"
        verbose_name = "a2.Division"
        ordering = ("id",)

    def __str__(self):
        return self.division_name

    def get_div_comp(self):
        return self.company
