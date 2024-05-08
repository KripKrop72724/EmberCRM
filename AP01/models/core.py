from django.contrib.auth.models import AbstractUser, Group
from django.db import models
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel


class User(AbstractUser):
    email = models.EmailField(unique=False)  # Tolerance added in serializer.
    otp = models.CharField(db_column="cotp", max_length=6, blank=True, null=True)
    phone_number = models.CharField(
        db_column="cphone", max_length=12, unique=True, null=True
    )
    otp_expire_at = models.DateTimeField(db_column="dexpire", blank=True, null=True)
    stripe_customer_id = models.CharField(max_length=50, blank=True, null=True)

    class Meta(AbstractUser.Meta):
        ordering = ("username",)


class T01Pkg10(models.Model):
    name = models.CharField(max_length=60, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    hide_phone_numbers = models.BooleanField(default=False)
    hide_comments = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class T01Com10(MPTTModel):
    users = models.ManyToManyField(User, blank=True, related_name="companies")

    parent = TreeForeignKey(
        "self", models.PROTECT, db_column="IDParentCo", blank=True, null=True
    )
    FYBEGIN_CHOICE = (
        (1, "Jan"),
        (2, "Feb"),
        (3, "Mar"),
        (4, "Apr"),
        (5, "May"),
        (6, "Jun"),
        (7, "Jul"),
        (8, "Aug"),
        (9, "Sep"),
        (10, "Oct"),
        (11, "Nov"),
        (12, "Dec"),
    )
    finyear_begin = models.IntegerField(
        db_column="nFYbegin", choices=FYBEGIN_CHOICE, null=True
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
    cost_type_co = models.IntegerField(
        db_column="nBuCstType", blank=True, null=True
    )  # average, fifo, fefo
    cost_level_co = models.IntegerField(
        db_column="nBuCstLevel", blank=True, null=True
    )  # cost by comp, div, wh
    active_status = models.BooleanField(db_column="bCompStatus", default=True)

    stripe_id = models.CharField(
        db_column="stripe_id", max_length=50, blank=True, editable=False
    )

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
    robo_nick_name = models.CharField(
        db_column="sRoboName", max_length=10, default="ebos"
    )
    email_sender = models.EmailField(db_column="eEmail", max_length=100, null=True)
    password_sender = models.CharField(db_column="cpassword", max_length=100, null=True)
    display_print_in_new_tab = models.BooleanField(
        db_column="bDisplayPrtTab", default=True
    )

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
    currency = models.ForeignKey(
        "T01Cur10", models.PROTECT, db_column="IDDivCurr", null=True
    )
    wps_mol_uid = models.CharField(
        db_column="sMolRegEmpr", max_length=50, blank=True
    )  # Ministry of Labour ref
    wps_bank_code = models.ForeignKey(
        "T01Bnk10",
        on_delete=models.SET_NULL,
        db_column="IDPrlBnk",
        null=True,
        blank=True,
        related_name="payroll_bank_acc",
    )
    cost_type_div = models.IntegerField(
        db_column="nBuCstType", blank=True, null=True
    )  # average, fifo, fefo
    cost_level_div = models.IntegerField(
        db_column="nBuCstLevel", blank=True, null=True
    )  # cost by comp, div, wh
    checklist_popup = models.BooleanField(
        db_column="bChecklist", default=False
    )  # checklist before saving
    convert_to_caps = models.IntegerField(
        db_column="nCap", blank=True, null=True
    )  # 1 Caps, 2 Small, 0 doNothing
    invoice_ref_flag = models.BooleanField(db_column="bBuInvRef", null=True)
    sellprice_flag = models.BooleanField(
        db_column="bBuSellPrice", blank=True, null=True
    )
    user = models.ManyToManyField(
        User, db_column="IDUsers", blank=True, related_name="users"
    )
    permission_data = models.JSONField(blank=True, null=True)
    ngrock = models.CharField(db_column="ngrockURL", max_length=420, blank=True, null=True)
    hide_header = models.BooleanField(null=True, blank=True, default=False)

    class Meta:
        #   managed = False  # reqd for existing DB with data, DB creation/modification/deletion handled manually
        db_table = "T01DIV10"
        verbose_name = "a2.Division"
        ordering = ("id",)

    def __str__(self):
        return self.division_name

    def get_div_comp(self):
        return self.company
