import csv
import os
from datetime import timedelta
from io import StringIO
import requests
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import models
from django.db.models import Max, Min
from django.dispatch import receiver
from django.utils import timezone
from simple_history.models import HistoricalRecords
from EmberCRM import settings
from AP01.models.core import T01Div10, T01Com10
from AP01.models.base import T01Lan10, T01Slm10, T01Nat10
from AP01.notification import send_email_formatted
from AP01.storage_backends import SecureFileSystemStorage

# Customer support stuff starts here >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

User = get_user_model()


class CustomerTicket(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    COMPANY_CHOICES = [
        ('Hogar', 'Hogar'),
        ('Aiems', 'Aiems'),
        ('Map', 'Map'),
        ('Mumayaz', 'Mumayaz'),
        ('Wecare', 'Wecare'),
        ('Alfalmonkey', 'Alfalmonkey'),
        ('NoonKebab', 'NoonKebab'),
        ('Ajman', 'Ajman'),  # For AMVT system
    ]

    ASSIGNEE_CHOICES = [
        ('Asad', 'Asad'),
        ('May', 'May'),
        ('Usama', 'Usama'),
        ('Mani', 'Mani'),
        ('Ubaid', 'Ubaid'),
        ('Raed', 'Raed'),
    ]

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in-progress', 'In Progress'),
        ('closed', 'Closed'),
        ('re-opened', 'Re-opened'),
        ('paused', 'paused'),
    ]

    TYPE_CHOICES = [
        ('bug', 'Bug'),
        ('stopping issue', 'stopping issue'),
        ('change request', 'change request'),
        ('enhancement', 'enhancement'),
        ('new-feature', 'new-feature'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets', null=True, blank=True)
    assignee = models.CharField(max_length=20, choices=ASSIGNEE_CHOICES, default='Asad')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='low')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    company = models.ForeignKey(T01Com10, on_delete=models.PROTECT, related_name='tickets', null=True, blank=True)
    problem_description = models.TextField()
    subject = models.CharField(max_length=200, null=True, blank=True)
    picture = models.FileField(upload_to='ticket_pictures/', null=True, blank=True)
    ticket_date = models.DateField(default=timezone.now, blank=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, null=True, blank=True)
    initial_estimate_hrs = models.IntegerField(null=True, blank=True)
    finalized_estimate_hrs = models.IntegerField(null=True, blank=True)
    start_date_time = models.DateTimeField(null=True, blank=True)
    close_date_time = models.DateTimeField(blank=True, null=True)
    pause_time = models.IntegerField(null=True, blank=True)
    affected_company = models.CharField(max_length=20, choices=COMPANY_CHOICES, null=True, blank=True,
                                        verbose_name="Company")
    requested_date = models.DateTimeField(null=True, blank=True, verbose_name="Date Requested by Client")
    comitted_date = models.DateTimeField(null=True, blank=True, verbose_name="Date Committed")
    history = HistoricalRecords()

    def __str__(self):
        return f"Ticket #{self.id}"  # by {self.assigned_to.username} - {self.status}"


class TicketReply(models.Model):
    reply_content = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='replies')
    reply_to = models.ForeignKey(CustomerTicket, on_delete=models.PROTECT, related_name='replies')
    history = HistoricalRecords()

    def __str__(self):
        return f"Reply #{self.id} by {self.user.username} to Ticket #{self.reply_to.id}"


# contact company / agents / freelancer group ...etc
class T02Cnt10(models.Model):
    division = models.ForeignKey(T01Div10, models.PROTECT, db_column='IdDivCnt', null=True)
    contact_name = models.CharField(db_column='sName', max_length=50, blank=True)
    short_name = models.CharField(db_column='sNameShort', max_length=5, blank=True)
    address_line1 = models.CharField(db_column='sAddr1', max_length=50, blank=True)
    address_line2 = models.CharField(db_column='sAddr2', max_length=50, blank=True)
    address_line3 = models.CharField(db_column='sAddr3', max_length=50, blank=True)
    contact_number = models.BigIntegerField(db_column='nCntNo', null=True)
    telephone = models.CharField(db_column='sTel', max_length=25, blank=True)
    fax = models.CharField(db_column='sFax', max_length=25, blank=True)
    email = models.CharField(db_column='sEmail', max_length=50, blank=True)
    mobile = models.CharField(db_column='sMobile', max_length=30, blank=True)
    gender = models.CharField(db_column='sSex', max_length=6, blank=True)
    postal_code = models.CharField(db_column='sPostCode', max_length=30, blank=True)
    region = models.CharField(db_column='sRegion', max_length=50, blank=True)
    website = models.CharField(db_column='sWebsite', max_length=50, blank=True)
    city = models.CharField(db_column='sCity', max_length=50, blank=True)
    attn_To = models.CharField(db_column='sAttnTo', max_length=50, blank=True)
    nationality = models.ForeignKey(T01Nat10, models.SET_NULL, db_column='IDNAT10', null=True)
    status = models.IntegerField(db_column='nStatus', blank=True, null=True)
    history = HistoricalRecords()

    class Meta:
        db_table = 'T02CNT10'
        verbose_name = 'a2.Contact Master'

    def __str__(self):
        return f"{self.division} - {self.contact_number}"


# multiple contacts in one company / agent / freelancer group
class T02Cnt11(models.Model):
    contact_master = models.ForeignKey(T02Cnt10, models.CASCADE, db_column='IDCnt10', null=True)
    name = models.CharField(db_column='sName', max_length=50)
    mobile = models.CharField(db_column='sMob', max_length=25)
    email = models.CharField(db_column='sEmail', max_length=50, blank=True)
    designation = models.CharField(db_column='sDesignation', max_length=50, blank=True)
    telephone = models.CharField(db_column='sTelNo', max_length=50, blank=True)
    history = HistoricalRecords()

    class Meta:
        db_table = 'T02CNT11'
        verbose_name = 'Contact Person'

    def __str__(self) -> str:
        return self.name


class ContactPerson(models.Model):
    name = models.CharField(max_length=200, null=False, blank=False)  # required
    mobile = models.CharField(max_length=20, null=False, blank=False)  # required
    email = models.EmailField(max_length=100, null=True, blank=True)  # optional
    designation = models.CharField(max_length=200, null=True, blank=True)  # optional
    telephone = models.CharField(max_length=20, null=True, blank=True)  # optional
    history = HistoricalRecords()

    def __str__(self):
        return self.name


class LeadStatusMaster(models.Model):
    status = models.CharField(max_length=100)
    color = models.CharField(max_length=100, null=True, blank=True)
    is_start = models.BooleanField(default=False, null=True, blank=True)
    is_end = models.BooleanField(default=False, null=True, blank=True)
    order = models.IntegerField(null=True, blank=True)
    is_assigned_status = models.BooleanField(default=False, null=True, blank=True)
    is_junk = models.BooleanField(default=False, null=True, blank=True)
    history = HistoricalRecords()

    def clean(self):
        # Ensure that only one LeadStatusMaster can be marked as start or end
        if self.is_start and LeadStatusMaster.objects.filter(is_start=True).exclude(pk=self.pk).exists():
            raise ValidationError('There can only be one start status.')
        if self.is_end and LeadStatusMaster.objects.filter(is_end=True).exclude(pk=self.pk).exists():
            raise ValidationError('There can only be one end status.')

    def save(self, *args, **kwargs):
        self.full_clean()
        super(LeadStatusMaster, self).save(*args, **kwargs)

    def __str__(self):
        return self.status

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['is_start'], condition=models.Q(is_start=True), name='unique_start_status'),
            models.UniqueConstraint(fields=['is_end'], condition=models.Q(is_end=True), name='unique_end_status')
        ]


class LeadCatMaster(models.Model):
    name = models.CharField(max_length=100)
    history = HistoricalRecords()

    def __str__(self):
        return self.name


class DealStagesMaster(models.Model):
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=100, null=True, blank=True)
    order = models.IntegerField(null=True, blank=True)
    is_start = models.BooleanField(default=False, null=True, blank=True)
    is_end = models.BooleanField(default=False, null=True, blank=True)
    is_lost = models.BooleanField(default=False, null=True, blank=True)
    history = HistoricalRecords()

    def __str__(self):
        return self.name


class CRMProduct(models.Model):
    name = models.CharField(max_length=100)
    off_plan_project = models.CharField(max_length=100, null=True, blank=True)
    developer = models.CharField(max_length=100, null=True, blank=True)
    property_status = models.CharField(max_length=100, null=True, blank=True)
    off_plan_type = models.CharField(max_length=100, null=True, blank=True)
    unit_type = models.CharField(max_length=100, null=True, blank=True)
    number_of_bedrooms = models.CharField(max_length=100, null=True, blank=True)
    custom_fields = models.JSONField(default=dict, null=True, blank=True)
    history = HistoricalRecords()

    def __str__(self):
        return self.name


class LeadQuestion(models.Model):
    question_text = models.TextField()
    order = models.IntegerField(unique=True, null=True, blank=True)
    history = HistoricalRecords()

    def __str__(self):
        return self.question_text


class T02Led10(models.Model):
    division = models.ForeignKey(T01Div10, models.PROTECT, db_column='IdDiv', null=True)
    contact = models.ForeignKey('T02Cnt10', models.SET_NULL, db_column='IdCnt', null=True, blank=True)
    first_name = models.CharField(db_column='sNameF', max_length=255, blank=True)
    last_name = models.CharField(db_column='sNameL', max_length=255, blank=True)
    email = models.CharField(db_column='eEmail', max_length=500, null=True, blank=True)
    phone = models.CharField(db_column='sPhone', max_length=500)
    language = models.ForeignKey(T01Lan10, models.SET_NULL, db_column='IdLan', null=True, blank=True)
    lead_status = models.ForeignKey(LeadStatusMaster, on_delete=models.SET_NULL, related_name='leads', null=True,
                                    blank=True)
    lead_category = models.ForeignKey(LeadCatMaster, on_delete=models.SET_NULL, related_name='leads', null=True,
                                      blank=True)
    lead_source = models.ForeignKey('T02Evt10', models.SET_NULL, db_column='IdEvt', null=True, blank=True)  # From event
    pipeline = models.ForeignKey('T02Pil10', models.SET_NULL, db_column='IdPil', null=True, blank=True)
    city = models.CharField(db_column='sCity', max_length=40, blank=True)
    country = models.CharField(db_column='sCountry', max_length=40, blank=True)
    website = models.CharField(db_column='sWebsite', max_length=60, blank=True)
    description = models.TextField(db_column='tDesc', blank=True)
    assigned_to = models.ForeignKey(T01Slm10, models.SET_NULL, db_column='IdSlm', null=True, blank=True,
                                    related_name='assigned_to')
    opportunity_amount = models.TextField(db_column='oppAmt', blank=True, null=True)
    generated_by = models.CharField(db_column='sGenBy', max_length=80, blank=True)
    created_on = models.DateTimeField(db_column='dCreatedOn', auto_now_add=True)
    enquiry_type = models.CharField(db_column='sEnqType', max_length=40, blank=True)
    IND_CHOICE = (("ADVERTISING", "ADVERTISING"),
                  ("REAL_ESTATE", "REAL_ESTATE"),
                  ("RETAIL", "RETAIL"),
                  ("AUTOMOTIVE", "AUTOMOTIVE"),
                  ("BANKING", "BANKING"),
                  ("CONTRACTING", "CONTRACTING"),
                  ("DISTRIBUTOR", "DISTRIBUTOR"),
                  ("SERVICES", "SERVICES"),
                  ("OTHERS", "OTHERS"))
    industry = models.CharField(db_column='sIndstry', max_length=20, choices=IND_CHOICE, blank=True)

    MRK_CHOICE = (("OFF PLAN", "OFF PLAN"),
                  ("SECONDARY", "SECONDARY"))
    market_choice = models.CharField(db_column='mChoice', max_length=20, choices=MRK_CHOICE, blank=True)

    is_contact = models.BooleanField(db_column='bIsContact', default=False)
    contact_persons = models.ManyToManyField(ContactPerson, related_name='leads', blank=True)
    primary_mobile = models.CharField(db_column='primaryPhone', max_length=1000, blank=True)
    secondary_mobile = models.CharField(db_column='secondaryPhone', max_length=1000, blank=True)
    date_of_birth = models.DateField(db_column='dateOfBirth', blank=True, null=True)

    last_rotation_time = models.DateTimeField(null=True, blank=True)
    has_deal = models.BooleanField(db_column='bHasDeal', default=False, blank=True, null=True)
    has_multiple = models.BooleanField(db_column='bHasMultipleDeal', default=False, blank=True, null=True)

    history = HistoricalRecords()

    class Meta:
        db_table = 'T02LED10'
        verbose_name = 'b1.Lead'

    def __str__(self):
        return str(self.first_name) + str(self.last_name)

    def total_clicks(self):
        # This will return the total number of interactions for the lead.
        return LeadInteraction.objects.filter(lead=self).count()

    def total_clicks_by_salesperson(self):
        # This will return a QuerySet with the salesperson and their total clicks for this lead.
        from django.db.models import Count
        return self.interactions.values('interacted_by__first_name', 'interacted_by__last_name') \
            .annotate(total_clicks=Count('id')) \
            .order_by('-total_clicks')


# for tracking
class LeadAssignmentHistory(models.Model):
    lead = models.ForeignKey(T02Led10, on_delete=models.CASCADE, related_name='assignment_history')
    salesperson = models.ForeignKey(T01Slm10, on_delete=models.CASCADE, related_name='lead_assignment_history')
    assigned_on = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        db_table = 'lead_assignment_history'
        verbose_name = 'Lead Assignment History'
        verbose_name_plural = 'Lead Assignment Histories'

    def __str__(self):
        return f"{self.lead} - {self.salesperson} - {self.assigned_on.strftime('%Y-%m-%d %H:%M:%S')}"


class LeadClickStats(models.Model):
    clicked_by = models.ForeignKey(T01Slm10, on_delete=models.CASCADE, related_name='click_stats')
    clicked_on = models.ForeignKey(T02Led10, on_delete=models.CASCADE, related_name='click_stats')
    clicked_at = models.DateTimeField(default=timezone.now)
    registered_flag = models.BooleanField(default=True)
    history = HistoricalRecords()

    class Meta:
        db_table = 'lead_click_stats'
        verbose_name = 'Lead Click Statistic'

    def __str__(self):
        return f"{self.clicked_by} clicked on {self.clicked_on} at {self.clicked_at}"

    def save(self, *args, **kwargs):
        # Ensure timezone awareness
        current_click_time = self.clicked_at if self.clicked_at else timezone.now()

        # Get the most recent click on the same lead by the same salesperson
        most_recent_click = LeadClickStats.objects.filter(
            clicked_by=self.clicked_by,
            clicked_on=self.clicked_on,
            clicked_at__lt=current_click_time
        ).aggregate(Max('clicked_at'))['clicked_at__max']

        # Check if the most recent click was more than 1 minute ago
        if most_recent_click:
            one_minute_ago = current_click_time - timedelta(minutes=1)
            self.registered_flag = most_recent_click < one_minute_ago
        else:
            # This means it's the first click by this user on this lead
            self.registered_flag = True

        super(LeadClickStats, self).save(*args, **kwargs)


class LeadAnswer(models.Model):
    lead = models.ForeignKey(T02Led10, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(LeadQuestion, on_delete=models.CASCADE)
    answer_text = models.TextField()
    history = HistoricalRecords()

    class Meta:
        unique_together = ['lead', 'question']

    def __str__(self):
        return f"{self.lead}: {self.question}"


class LeadNote(models.Model):
    lead = models.ForeignKey(T02Led10, on_delete=models.CASCADE, db_column='LeadId',
                             related_name='notes')  # Change related_name
    note = models.TextField(db_column='tNote')
    created_on = models.DateTimeField(db_column='dCreatedOn', auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="created_notes")
    history = HistoricalRecords()

    class Meta:
        db_table = 'LeadNotes'
        verbose_name = 'Lead Note'


class LeadAssignment(models.Model):
    lead = models.ForeignKey(T02Led10, on_delete=models.CASCADE, related_name='assignments')
    assigned_to = models.ForeignKey(T01Slm10, on_delete=models.CASCADE, related_name='lead_assignments')
    assigned_on = models.DateTimeField(auto_now_add=True)
    unassigned_on = models.DateTimeField(null=True, blank=True)  # To track when a lead is unassigned

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.lead} assigned to {self.assigned_to} on {self.assigned_on}"

    def time_to_first_interaction(self):
        first_interaction = self.lead.interactions.filter(interacted_by=self.assigned_to) \
            .aggregate(first_interaction_time=Min('interaction_time')) \
            .get('first_interaction_time', None)
        if first_interaction:
            # Calculate the time difference between the assignment and the first interaction in your preferred format
            time_difference = first_interaction - self.assigned_on
            return time_difference
        return None

    class Meta:
        db_table = 'LeadAssignments'
        verbose_name = 'Lead Assignment'


class LeadInteraction(models.Model):
    lead = models.ForeignKey(T02Led10, on_delete=models.CASCADE, related_name='interactions')
    interaction_type = models.CharField(max_length=20,
                                        choices=(('click_lead', 'Click on Lead'), ('view_phone', 'View Phone Number'),))
    interaction_time = models.DateTimeField(auto_now_add=True)
    interacted_by = models.ForeignKey(T01Slm10, on_delete=models.SET_NULL, null=True, related_name='interactions')

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.interaction_type} on {self.lead} by {self.interacted_by} at {self.interaction_time}"

    class Meta:
        db_table = 'LeadInteractions'
        verbose_name = 'Lead Interaction'


class LeadInteractionTime(models.Model):
    lead_assignment = models.OneToOneField(LeadAssignment, on_delete=models.CASCADE, related_name='interaction_time')
    time_to_first_click = models.DurationField(null=True, blank=True)
    time_to_first_view_phone = models.DurationField(null=True, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    def save(self, *args, **kwargs):
        if not self.pk:  # If this is the first time the object is created
            first_click = self.lead_assignment.lead.interactions.filter(
                interacted_by=self.lead_assignment.assigned_to,
                interaction_type='click_lead'
            ).order_by('interaction_time').first()

            first_view_phone = self.lead_assignment.lead.interactions.filter(
                interacted_by=self.lead_assignment.assigned_to,
                interaction_type='view_phone'
            ).order_by('interaction_time').first()

            if first_click:
                self.time_to_first_click = first_click.interaction_time - self.lead_assignment.assigned_on

            if first_view_phone:
                self.time_to_first_view_phone = first_view_phone.interaction_time - self.lead_assignment.assigned_on

        super().save(*args, **kwargs)  # Call the "real" save() method.

    def __str__(self):
        return f"{self.lead_assignment.lead} - Time to First Click: {self.time_to_first_click}, Time to First Phone View: {self.time_to_first_view_phone}"

    class Meta:
        db_table = 'lead_interaction_times'
        verbose_name = 'Lead Interaction Time'


class T02Opp10(models.Model):
    division = models.ForeignKey(T01Div10, models.PROTECT, db_column='IdDiv', null=True)
    lead = models.ForeignKey(T02Led10, models.SET_NULL, db_column='IdLed', null=True, blank=True)
    opportunity_name = models.CharField(db_column='sOppName', max_length=255)
    pipeline_stage = models.ForeignKey('T02Pil10', models.SET_NULL, db_column='IdPil', null=True, blank=True)
    CURRENCY_CHOICE = (('AED', 'AED'), ('EUR', 'EUR'), ('USD', 'USD'), ('GBP', 'GBP'))
    currency = models.CharField(db_column='sCurr', max_length=3, choices=CURRENCY_CHOICE, blank=True)
    amount = models.IntegerField(db_column='nAmt', blank=True, default=0)
    probability = models.IntegerField(db_column='nProb', default=0)
    description = models.TextField(db_column='tDesc', blank=True)
    created_on = models.DateTimeField(db_column='dtCreatedOn', auto_now_add=True)
    target_date = models.DateField(db_column='dTrgtdte', blank=True, null=True)
    closed_on = models.DateField(db_column='dClosedOn', blank=True, null=True)
    CLOSING_STATUS_CHOICE = (
        ('In-Progress', 'In-Progress'), ('Closed-Won', 'Closed-Won'), ('Closed-Lost', 'Closed-Lost'))
    closing_status = models.CharField(db_column='sClsStatus', max_length=20, choices=CLOSING_STATUS_CHOICE,
                                      default='In-Progress')
    history = HistoricalRecords()

    class Meta:
        db_table = 'T02OPP10'
        verbose_name = 'b2.Opportunity'

    def __str__(self):
        return self.opportunity_name


class T02Evt10(models.Model):
    event_name = models.CharField(db_column='sEvtName', max_length=255)
    EVENT_TYPE = (
        ("telecalling", "Telecalling"),
        ("visit", "Visit"),
        ("call", "Call"),
        ('email', 'Email'),
        ('webad', 'Web Advt')
    )
    event_type = models.CharField(db_column='sEvtType', max_length=25, choices=EVENT_TYPE)
    EVENT_STATUS = (
        ("Planned", "Planned"),
        ("Held", "Held"),
        ("Not Held", "Not Held"),
        ("Not Started", "Not Started"),
        ("Started", "Started"),
        ("Completed", "Completed"),
        ("Canceled", "Canceled"),
        ("Deferred", "Deferred"),
    )
    status = models.CharField(db_column='sEvtStats', choices=EVENT_STATUS, max_length=25, blank=True, null=True)
    start_date = models.DateTimeField(db_column='dtSrtdtetm', blank=True, null=True)
    end_date = models.DateTimeField(db_column='dtEndDteTm', blank=True, null=True)
    description = models.TextField(db_column='tDesc', blank=True, null=True)
    division = models.ForeignKey(T01Div10, models.PROTECT, db_column='IdDiv', null=True)
    history = HistoricalRecords()

    class Meta:
        db_table = 'T02EVT10'
        verbose_name = 'a1.Marketing Event'

    def __str__(self):
        return self.event_type


class T02Tsk10(models.Model):
    task_name = models.CharField(db_column='sTaskName', max_length=255, null=True)
    division = models.ForeignKey(T01Div10, models.PROTECT, db_column='IdDiv', null=True)
    opportunity = models.ForeignKey(T02Opp10, models.CASCADE, related_name='tasks', db_column='IdOpp', null=True)
    lead = models.ForeignKey(T02Led10, models.CASCADE, db_column='IdLed', null=True)
    STATUS_CHOICES = (
        ("New", "New"),
        ("In Progress", "In Progress"),
        ("Completed", "Completed"),
    )
    PRIORITY_CHOICES = (("Low", "Low"), ("Medium", "Medium"), ("High", "High"))
    TASKTYPE_CHOICES = (
        ("call", "Call"),
        ("telephone call", "TelePhone Call"),
        ("email", "Email"),
        ("visit", "Visit"),
        ("meeting", "Meeting"),
        ("demo", "Demo"),
    )
    task_date = models.DateTimeField(db_column='dTskDt', blank=True, null=True)  # default current date
    task_type = models.CharField(db_column='sTskType', max_length=25, choices=TASKTYPE_CHOICES)
    task_notes = models.TextField(db_column='tTskNts', max_length=255, blank=True, null=True)
    status = models.CharField(db_column='sStatus', max_length=25, choices=STATUS_CHOICES)
    priority = models.CharField(db_column='sPriorty', max_length=25, choices=PRIORITY_CHOICES)
    due_date = models.DateTimeField(db_column='dduedt', blank=True, null=True)
    created_on = models.DateTimeField(db_column='dtCreatedOn', auto_now_add=True)
    event_link = models.TextField(db_column='sEvtLink', blank=True, null=True)
    event_id = models.TextField(db_column='sEvtId', blank=True, null=True)
    gmail_link = models.TextField(null=True, blank=True)
    creator = models.ForeignKey(User, models.PROTECT, db_column='IdUser', null=True, blank=True)
    history = HistoricalRecords()

    class Meta:
        db_table = 'T02TSK10'
        verbose_name = 'b3.Task'

    def __str__(self):
        return self.task_type


class T02Rem10(models.Model):
    reminder_date = models.DateTimeField(db_column='dtremdte', blank=True, null=True)
    reminder_type = models.CharField(db_column='sRemTyp', max_length=25, blank=True, null=True)
    task_to_remind = models.ForeignKey(T02Tsk10, models.PROTECT, db_column='IdTsk', null=True, blank=True)
    opportunity_follow = models.ForeignKey(T02Opp10, models.PROTECT, db_column='IdOpp', null=True, blank=True)
    lead_follow = models.ForeignKey(T02Led10, models.PROTECT, db_column='IdLed', null=True, blank=True)
    event_follow = models.ForeignKey(T02Evt10, models.PROTECT, db_column='Idevt', null=True, blank=True)
    history = HistoricalRecords()

    def __str__(self):
        return self.reminder_type


class T02Pil10(models.Model):
    pipeline_name = models.CharField(db_column='sPilName', max_length=255)
    target_days = models.IntegerField(db_column='nAllwDur', default=0)
    probability_percent = models.IntegerField(db_column='nProbPerc', default=10)
    is_active = models.BooleanField(db_column='bIsActive', default=False)
    history = HistoricalRecords()

    class Meta:
        db_table = 'T02PIL10'
        verbose_name = 'a4.Pipeline Setup'

    def __str__(self):
        return self.pipeline_name


# Reports Base Model
class T02Rpt10(models.Model):
    division = models.ForeignKey(T01Div10, models.PROTECT, db_column='IdDivCnt', null=True)
    date_from = models.DateField(db_column='dFrom', null=True)
    date_upto = models.DateField(db_column='dUpTo', null=True)
    rpt_code = models.CharField(db_column='sRptCode', max_length=3, blank=True, null=True)
    report_csv = models.FileField(db_column='flSlAcRpt', upload_to='sales_reports', null=True, blank=True)

    class Meta:
        db_table = 'T02RPT10'
        verbose_name = 'c0.Sales Report'


# Sales Action Report
class T02Sat10Manager(models.Manager):
    def get_queryset(self):
        return super(T02Sat10Manager, self).get_queryset().filter(rpt_code='SAR')


class T02Sat10(T02Rpt10):
    objects = T02Sat10Manager()

    class Meta:
        proxy = True
        verbose_name = 'c1.Sales Action Report'

    def save(self, *args, **kwargs):
        self.rpt_code = 'SAR'
        super(T02Sat10, self).save(*args, **kwargs)


# Sales forecast Report
class T02Sfc10Manager(models.Manager):
    def get_queryset(self):
        return super(T02Sfc10Manager, self).get_queryset().filter(rpt_code='SFR')


class T02Sfc10(T02Rpt10):
    objects = T02Sfc10Manager()

    class Meta:
        proxy = True
        verbose_name = 'c2.Sales Forecast Report'

    def save(self, *args, **kwargs):
        self.rpt_code = 'SFR'
        super(T02Sfc10, self).save(*args, **kwargs)


# Pipeline Status based on Leads
class T02Plr10Manager(models.Manager):
    def get_queryset(self):
        return super(T02Plr10Manager, self).get_queryset().filter(rpt_code='PLR')


class T02Plr10(T02Rpt10):
    objects = T02Plr10Manager()

    class Meta:
        proxy = True
        verbose_name = 'c3.Pipeline Status based on Lead'

    def save(self, *args, **kwargs):
        self.rpt_code = 'PLR'
        super(T02Plr10, self).save(*args, **kwargs)


# Pipeline Status based on Opportunities
class T02Por10Manager(models.Manager):
    def get_queryset(self):
        return super(T02Por10Manager, self).get_queryset().filter(rpt_code='POR')


class T02Por10(T02Rpt10):
    objects = T02Por10Manager()

    class Meta:
        proxy = True
        verbose_name = 'c4.Pipeline Status based on Opportunity'

    def save(self, *args, **kwargs):
        self.rpt_code = 'POR'
        super(T02Por10, self).save(*args, **kwargs)


# Opportunity Review Report
class T02Opr10Manager(models.Manager):
    def get_queryset(self):
        return super(T02Opr10Manager, self).get_queryset().filter(rpt_code='ORR')


class T02Opr10(T02Rpt10):
    objects = T02Opr10Manager()

    class Meta:
        proxy = True
        verbose_name = 'c5.Opportunity Review Report'

    def save(self, *args, **kwargs):
        self.rpt_code = 'ORR'
        super(T02Opr10, self).save(*args, **kwargs)


#### Actions Post Save of Proxy Models
@receiver(models.signals.post_save, sender=T02Sat10)
@receiver(models.signals.post_save, sender=T02Sfc10)
@receiver(models.signals.post_save, sender=T02Plr10)
@receiver(models.signals.post_save, sender=T02Por10)
@receiver(models.signals.post_save, sender=T02Opr10)
def sales_reports(sender, instance, **kwargs):
    division = instance.division
    date_from = instance.date_from
    date_upto = instance.date_upto
    reports = T02Rpt10.objects.filter(id=instance.id)

    if reports.filter(rpt_code='SAR').exists():
        name = "sales_action_report"
        response = StringIO()
        writer = csv.writer(response)

        # Adding Task record heading to csv
        writer.writerow(
            ['Opportunity', 'Lead', 'Task Type', 'Task Notes', 'Status', 'Priority', 'Due Date', 'Created On'])

        values_list = []

        # filter division = input_division, task_create_date = input_date and pipleline <= 90
        T02Tsk10_records = T02Tsk10.objects.filter(created_on__date__gte=date_from, created_on__date__lte=date_upto,
                                                   opportunity__pipeline_stage__probability_percent__lte=90,
                                                   opportunity__lead__contact__division=division)

        # Adding Task record values to csv
        for T02Tsk10_record in T02Tsk10_records:
            values = (T02Tsk10_record.id, T02Tsk10_record.opportunity, T02Tsk10_record.lead, T02Tsk10_record.task_type,
                      T02Tsk10_record.task_notes,
                      T02Tsk10_record.status, T02Tsk10_record.priority, T02Tsk10_record.due_date,
                      T02Tsk10_record.created_on)
            values_list.append(values)

        for value in values_list:
            writer.writerow(value)

        csv_file = ContentFile(response.getvalue().encode('utf-8'))

    elif reports.filter(rpt_code='SFR').exists():
        name = "sales_forecast_report"
        response = StringIO()
        writer = csv.writer(response)
        writer.writerow(['Opportunity Name', 'Pipeline Stage', 'Currency', 'Amount',
                         'Probability', 'Description', 'Created On', 'Target Date', 'Closed On', 'Lead'])

        # filter division, pipeline prob > 50 and prob <= 90, target_date = input_date
        T02Opp10_records = T02Opp10.objects.filter(lead__contact__division=division,
                                                   pipeline_stage__probability_percent__lte=90,
                                                   pipeline_stage__probability_percent__gt=50,
                                                   target_date__gte=date_from,
                                                   target_date__lte=date_upto
                                                   )
        values_list = []

        for T02Opp10_record in T02Opp10_records:
            values = (T02Opp10_record.opportunity_name, T02Opp10_record.pipeline_stage, T02Opp10_record.currency,
                      T02Opp10_record.amount,
                      T02Opp10_record.probability, T02Opp10_record.description, T02Opp10_record.created_on,
                      T02Opp10_record.target_date,
                      T02Opp10_record.closed_on, T02Opp10_record.lead)
            values_list.append(values)

        for value in values_list:
            writer.writerow(value)

        csv_file = ContentFile(response.getvalue().encode('utf-8'))


    elif reports.filter(rpt_code='POR').exists():
        name = "pipeline_status_opportunities"
        response = StringIO()
        writer = csv.writer(response)
        pipleline_records = T02Pil10.objects.all().values('id').distinct()
        # Report on basis of Opportunities
        values_list = []
        for pipleline_record in pipleline_records:
            writer.writerow(['PIPELINE NAME', 'TARGET DAYS', 'PROBABILITY PERCENT', 'IS ACTIVE'])
            get_pipeline_data = T02Pil10.objects.get(id=pipleline_record.get('id'))
            value = (get_pipeline_data.pipeline_name, get_pipeline_data.target_days,
                     get_pipeline_data.probability_percent, get_pipeline_data.is_active)
            writer.writerow(value)
            writer.writerow("")
            writer.writerow(['OPPORTUNITY NAME', 'PIPELINE STAGE', 'CURRENCY', 'AMOUNT', 'PROBABILITY', 'DESCRIPTION',
                             'CREATED ON', 'TARGET DATE', 'CLOSED ON'])

            values_list = []
            get_oppor = T02Opp10.objects.filter(pipeline_stage=get_pipeline_data.id)
            for oppor in get_oppor:
                child_values = (
                    oppor.opportunity_name, oppor.pipeline_stage, oppor.currency, oppor.amount, oppor.probability,
                    oppor.description, oppor.created_on, oppor.target_date, oppor.closed_on)
                values_list.append(child_values)

            for child_data in values_list:
                writer.writerow(child_data)

            writer.writerow("")
            writer.writerow("")

        csv_file = ContentFile(response.getvalue().encode('utf-8'))

    elif reports.filter(rpt_code='PLR').exists():
        name = "pipeline_status_leads"
        pipleline_records = T02Pil10.objects.all().values('id').distinct()
        response = StringIO()
        writer = csv.writer(response)
        values_list = []
        for pipleline_record in pipleline_records:
            writer.writerow(['PIPELINE NAME', 'TARGET DAYS', 'PROBABILITY PERCENT', 'IS ACTIVE'])
            get_pipeline_data = T02Pil10.objects.get(id=pipleline_record.get('id'))
            value = (get_pipeline_data.pipeline_name, get_pipeline_data.target_days,
                     get_pipeline_data.probability_percent, get_pipeline_data.is_active)
            writer.writerow(value)
            writer.writerow("")
            writer.writerow(
                ['CONTACT', 'FIRST NAME', 'LAST NAME', 'EMAIL', 'PHONE', 'LANGUAGE', 'LEAD STATUS', 'LEAD SOURCE',
                 'CITY', 'COUNTRY', 'WEBSITE', 'DESCRIPTION', 'ASSIGNED TO', 'OPPORUNITY AMOUNT', 'GENERATED BY',
                 'CREATED ON', 'ENQUIRY TYPE', 'INDUSTRY'])
            values_list = []
            get_Leads = T02Led10.objects.filter(pipeline=get_pipeline_data.id)
            for get_Lead in get_Leads:
                child_values = (
                    get_Lead.contact, get_Lead.first_name, get_Lead.last_name, get_Lead.email, get_Lead.phone,
                    get_Lead.language, get_Lead.lead_status, get_Lead.lead_source, get_Lead.city, get_Lead.country,
                    get_Lead.website, get_Lead.description, get_Lead.assigned_to, get_Lead.opportunity_amount,
                    get_Lead.generated_by, get_Lead.created_on, get_Lead.enquiry_type, get_Lead.industry)
                values_list.append(child_values)

            for child_data in values_list:
                writer.writerow(child_data)

            writer.writerow("")
            writer.writerow("")

        csv_file = ContentFile(response.getvalue().encode('utf-8'))

    elif reports.filter(rpt_code='ORR').exists():
        name = "opportunity_review_report"
        response = StringIO()
        writer = csv.writer(response)
        writer.writerow(['Opportunity Name', 'Pipeline Stage', 'Currency', 'Amount',
                         'Probability', 'Description', 'Created On', 'Target Date', 'Closed On', 'Lead'])

        # filter division, opportunity prob <= 90 and prob > 10,
        T02Opp10_records = T02Opp10.objects.filter(lead__contact__division=division,
                                                   pipeline_stage__probability_percent__lte=90,
                                                   pipeline_stage__probability_percent__gt=10
                                                   )
        values_list = []
        for T02Opp10_record in T02Opp10_records:
            values = (T02Opp10_record.opportunity_name, T02Opp10_record.pipeline_stage, T02Opp10_record.currency,
                      T02Opp10_record.amount,
                      T02Opp10_record.probability, T02Opp10_record.description, T02Opp10_record.created_on,
                      T02Opp10_record.target_date,
                      T02Opp10_record.closed_on, T02Opp10_record.lead)
            values_list.append(values)

        for value in values_list:
            writer.writerow(value)

        csv_file = ContentFile(response.getvalue().encode('utf-8'))

    csv_file_name = f"sales_report/{name}_{str(instance.id)}.csv"

    if default_storage.exists(csv_file_name):
        default_storage.delete(csv_file_name)
    file_name = default_storage.save(csv_file_name, csv_file)

    # Update File Fields
    reports.update(report_csv=file_name)
    return True


# delete files when record delete from model...
@receiver(models.signals.post_delete, sender=T02Sat10)
@receiver(models.signals.post_delete, sender=T02Sfc10)
@receiver(models.signals.post_delete, sender=T02Plr10)
@receiver(models.signals.post_delete, sender=T02Por10)
@receiver(models.signals.post_delete, sender=T02Opr10)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    if instance.report_csv:
        if os.path.isfile(instance.report_csv.path):
            os.remove(instance.report_csv.path)


# Email Stuff Starts Here >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

class EmailTemplate(models.Model):
    template_name = models.CharField(max_length=255)
    template_content = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.template_name


class EmailSchedulerRooster(models.Model):
    template = models.ForeignKey(EmailTemplate, on_delete=models.CASCADE)
    send_datetime = models.DateTimeField()
    recipient = models.EmailField()
    subject = models.CharField(max_length=255)
    sent = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.template.template_name} to {self.recipient} at {self.send_datetime}'


class DealQuestion(models.Model):
    question_text = models.TextField()
    order = models.IntegerField(unique=True, null=True, blank=True)

    def __str__(self):
        return self.question_text


class T02DL10(models.Model):
    deal_value = models.CharField(max_length=5000, db_column='fDealValue')
    commission_percentage = models.DecimalField(max_digits=6, decimal_places=2, db_column='fCommPer', blank=True,
                                                null=True)
    sales_person = models.ForeignKey(T01Slm10, on_delete=models.SET_NULL, db_column='IdSlm', blank=True, null=True)
    lead_id = models.ForeignKey(T02Led10, on_delete=models.CASCADE, db_column='IdLed', related_name='deals')
    stage = models.ForeignKey(DealStagesMaster, on_delete=models.SET_NULL, db_column='IdStage', blank=True, null=True)
    product = models.ForeignKey(CRMProduct, on_delete=models.SET_NULL, db_column='IdProduct', blank=True, null=True)
    created_on = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    file = models.ImageField(upload_to='deal_files/', null=True, blank=True, storage=SecureFileSystemStorage())
    order = models.IntegerField(blank=True, null=True, unique=True)

    class Meta:
        db_table = 'T02DL10'
        verbose_name = 'Deal Master'

    def __str__(self):
        return f"Deal for {self.sales_person} - Value: {self.deal_value}"

    def save(self, *args, **kwargs):
        # Create a default product if none is assigned
        if not self.product_id:
            default_product, created = CRMProduct.objects.get_or_create(
                name="Default Product Name",
                defaults={
                    'off_plan_project': 'N/A',
                    'developer': 'N/A',
                    'property_status': 'N/A',
                    'off_plan_type': 'N/A',
                    'unit_type': 'N/A',
                    'number_of_bedrooms': 'N/A',
                    # Add other fields and default values as needed
                }
            )
            self.product = default_product

        super().save(*args, **kwargs)


class DealAnswer(models.Model):
    deal = models.ForeignKey(T02DL10, on_delete=models.CASCADE, related_name='deal_answers')
    question = models.ForeignKey(DealQuestion, on_delete=models.CASCADE)
    answer_text = models.TextField()

    class Meta:
        unique_together = ['deal', 'question']

    def __str__(self):
        return f"{self.deal}: {self.question}"


class SalesmanStats(models.Model):
    salesman = models.OneToOneField(T01Slm10, on_delete=models.CASCADE)
    total_leads = models.PositiveIntegerField(default=0)
    total_tasks = models.PositiveIntegerField(default=0)
    won_leads = models.PositiveIntegerField(default=0)
    lost_leads = models.PositiveIntegerField(default=0)
    closed_tasks = models.PositiveIntegerField(default=0)
    overdue_tasks = models.PositiveIntegerField(default=0)
    in_progress_tasks = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'T02SLMSTATS'
        verbose_name = 'SLM Stats'


# @receiver([post_save, post_delete, pre_save], sender=T02Led10)
# def lead_changed(sender, instance, **kwargs):
#     channel_layer = get_channel_layer()
#     async_to_sync(channel_layer.group_send)(
#         f"salesman_{instance.assigned_to_id}",
#         {
#             "type": "lead_task_changed",
#             "salesman_id": instance.assigned_to_id
#         }
#     )
#
#
# @receiver([post_save, post_delete, pre_save], sender=T02Tsk10)
# def task_changed(sender, instance, **kwargs):
#     channel_layer = get_channel_layer()
#     async_to_sync(channel_layer.group_send)(
#         f"salesman_{instance.lead.assigned_to_id}",
#         {
#             "type": "lead_task_changed",
#             "salesman_id": instance.lead.assigned_to_id
#         }
#     )

# @receiver(pre_save, sender=T02Led10)
# def lead_pre_save_handler(sender, instance, **kwargs):
#     print("Firing...")
#     try:
#         # store the old lead object before it is saved
#         instance._old_lead = T02Led10.objects.get(pk=instance.pk)
#     except T02Led10.DoesNotExist:
#         # This is a new object, so set _old_lead to None
#         instance._old_lead = None
#
#
# @receiver(post_save, sender=T02Led10)
# def update_salesman_stats_on_lead_save(sender, instance, created, **kwargs):
#     print("Firing...")
#
#     if not instance.assigned_to:
#         print("No salesman assigned. Exiting signal.")
#         return
#
#         # Check if assigned_to has actually changed
#     if not created and instance._old_lead and instance.assigned_to == instance._old_lead.assigned_to:
#         print("Assigned to has not changed. Exiting signal.")
#         return
#
#     with transaction.atomic():
#         stats, created_stats = SalesmanStats.objects.select_for_update().get_or_create(salesman=instance.assigned_to)
#         print(f"SalesmanStats object {'created' if created_stats else 'fetched'} for salesman {instance.assigned_to}")
#
#         if created:
#             stats.total_leads = F('total_leads') + 1
#             print("Incremented total_leads.")
#         else:
#             print("This is an update operation.")
#             old_salesman = instance._old_lead.assigned_to if instance._old_lead else None
#
#             if old_salesman and old_salesman != instance.assigned_to:
#                 old_stats, _ = SalesmanStats.objects.get_or_create(salesman=old_salesman)
#                 old_stats.total_leads = F('total_leads') - 1
#                 old_stats.save(update_fields=['total_leads'])
#                 print(f"SalesmanStats total_leads decremented for old salesman {old_salesman}")
#
#             old_status = instance._old_lead.lead_status.status if instance._old_lead and instance._old_lead.lead_status else None
#             new_status = instance.lead_status.status if instance.lead_status else None
#
#             if old_status != new_status:
#                 if old_status == "Closed Won":
#                     stats.won_leads = F('won_leads') - 1
#                 elif old_status == "Closed Lost":
#                     stats.lost_leads = F('lost_leads') - 1
#                 if new_status == "Closed Won":
#                     stats.won_leads = F('won_leads') + 1
#                 elif new_status == "Closed Lost":
#                     stats.lost_leads = F('lost_leads') + 1
#
#         stats.save(update_fields=['total_leads', 'won_leads', 'lost_leads'])
#         print("SalesmanStats saved successfully.")
#
#     # Outside the atomic block to ensure the transaction is committed
#     stats.refresh_from_db()
#     print("Debug: Re-fetched SalesmanStats:", stats)
#
#
# @receiver(post_delete, sender=T02Led10)
# def update_salesman_stats_on_lead_delete(sender, instance, **kwargs):
#     print("Firing...")
#     try:
#         stats = SalesmanStats.objects.get(salesman=instance.assigned_to)
#         stats.total_leads -= 1
#
#         if instance.lead_status.status == "Closed Won":
#             stats.won_leads -= 1
#         elif instance.lead_status.status == "Closed Lost":
#             stats.lost_leads -= 1
#
#         stats.save()
#     except Exception as e:
#         # log the error or handle it as per your requirements
#         print(f"Error in update_salesman_stats_on_lead_delete: {str(e)}")
#
#
# @receiver(post_save, sender=T02Tsk10)
# def update_salesman_stats_on_task_save(sender, instance, created, **kwargs):
#     print("Firing...")
#     try:
#         if instance.lead and instance.lead.assigned_to:
#             stats = SalesmanStats.objects.get(salesman=instance.lead.assigned_to)
#
#             if created:
#                 stats.total_tasks += 1
#
#             # Update task stats based on status
#             if instance.status == "Completed":
#                 stats.closed_tasks += 1
#             elif instance.due_date < timezone.now():
#                 stats.overdue_tasks += 1
#             else:
#                 stats.in_progress_tasks += 1
#
#             stats.save()
#     except Exception as e:
#         # log the error or handle it as per your requirements
#         print(f"Error in update_salesman_stats_on_task_save: {str(e)}")
#
#
# @receiver(post_delete, sender=T02Tsk10)
# def update_salesman_stats_on_task_delete(sender, instance, **kwargs):
#     print("Firing...")
#     try:
#         if instance.lead and instance.lead.assigned_to:
#             stats = SalesmanStats.objects.get(salesman=instance.lead.assigned_to)
#             stats.total_tasks -= 1
#
#             # Update task stats based on status
#             if instance.status == "Completed":
#                 stats.closed_tasks -= 1
#             elif instance.due_date < timezone.now():
#                 stats.overdue_tasks -= 1
#             else:
#                 stats.in_progress_tasks -= 1
#
#             stats.save()
#     except Exception as e:
#         # log the error or handle it as per your requirements
#         print(f"Error in update_salesman_stats_on_task_delete: {str(e)}")
#
#
# @receiver(pre_save, sender=T02Tsk10)
# def pre_save_task(sender, instance, **kwargs):
#     # If the task is being updated (not created)
#     print("Firing...")
#     if instance.pk:
#         # Fetch the old state of the task from the database
#         old_task = T02Tsk10.objects.get(pk=instance.pk)
#
#         # Store the old state in the instance to be accessed in the post_save signal
#         instance._old_status = old_task.status
#         instance._old_due_date = old_task.due_date
#         instance._old_salesman = old_task.lead.assigned_to if old_task.lead else None

class LeadRotationMaster(models.Model):
    STATUS_CHOICES = (
        ('on', 'On'),
        ('off', 'Off')
    )
    TRIG_CHOICES = (
        ('none', 'none'),
        ('Call Counter', 'Call Counter')
    )
    ROTATION_CRITERIA_CHOICES = (
        ('random', 'Random'),
        ('least_first', 'Least First'),
        ('most_first', 'Most First'),
        ('language_based', 'Language Based')
    )

    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    lead_status = models.OneToOneField(LeadStatusMaster, on_delete=models.CASCADE, unique=True)
    rotation_criteria = models.CharField(max_length=15, choices=ROTATION_CRITERIA_CHOICES)
    triggered_upon = models.CharField(max_length=25, choices=TRIG_CHOICES, null=True, blank=True)
    hours_to_rotate = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.lead_status.status} - {self.rotation_criteria} - Every {self.hours_to_rotate} hours"

    class Meta:
        verbose_name = 'Lead Rotation Rule'
        verbose_name_plural = 'Lead Rotation Rules'


class VideoCall(models.Model):
    lead = models.ForeignKey(T02Led10, on_delete=models.CASCADE)
    created_on = models.DateTimeField(auto_now_add=True)
    link = models.URLField()
    username = models.ForeignKey(User, on_delete=models.CASCADE)
    secondary_email = models.EmailField(blank=True, null=True)
    call_notes = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.link:
            # Call Daily API to create a video call room
            headers = {
                'Authorization': 'Bearer b62ca898a9f53055e0bdfa86e27354a25320d2a2eca80a2a845dba34ae5329c3',
                'Content-Type': 'application/json'
            }
            response = requests.post('https://api.daily.co/v1/rooms', headers=headers)
            if response.status_code == 200:
                self.link = response.json()['url']
            else:
                raise ValidationError({"error": "Video link cannot be created."})

        super(VideoCall, self).save(*args, **kwargs)

        # Send email notifications
        self.send_email_notifications()

    def send_email_notifications(self):
        subject = "Video Call Link"
        message = f"Please join the video call using this link: {self.link}"
        emails = [self.lead.email]
        if self.secondary_email:
            emails.append(self.secondary_email)
        send_email_formatted(subject, message, emails)


class Notification(models.Model):
    recipient = models.ForeignKey(T01Slm10, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_notifications')
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Notification from {self.sender.username} to {self.recipient.first_name} {self.recipient.last_name}"

    @classmethod
    def send_notification(cls, sender, recipient_id, message="You've been pinged!"):
        try:
            recipient = T01Slm10.objects.get(id=recipient_id)
            cls.objects.create(sender=sender, recipient=recipient, message=message)
        except T01Slm10.DoesNotExist:
            raise ValueError("Recipient not found")
        except Exception as e:
            # Handle other unforeseen exceptions
            raise Exception(f"An error occurred while sending notification: {e}")

    def mark_as_read(self):
        if not self.read:
            self.read = True
            self.read_at = timezone.now()
            self.save()

    def mark_as_read(self):
        try:
            self.read = True
            self.save()
        except Exception as e:
            # Handle potential exceptions during save
            raise Exception(f"An error occurred while marking notification as read: {e}")


class EchoData(models.Model):
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    migrated = models.BooleanField(default=False)

    def __str__(self):
        return f"EchoData {self.id} created at {self.created_at}"


User = get_user_model()


class PopNotification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='popnotifications', null=True, blank=True)
    salesman = models.ForeignKey(T01Slm10, on_delete=models.CASCADE, related_name='popnotifications', null=True,
                                 blank=True)
    lead = models.ForeignKey(T02Led10, on_delete=models.CASCADE, related_name='popnotifications', null=True, blank=True)
    is_read = models.BooleanField(default=False)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    task = models.ForeignKey(T02Tsk10, on_delete=models.CASCADE, related_name='popnotifications_task', null=True,
                             blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.salesman} - Read: {self.is_read}"


class LeadHistoryModel(models.Model):
    lead_id = models.ForeignKey(T02Led10, on_delete=models.CASCADE, blank=True, null=True)
    timestamp = models.DateTimeField()
    detail = models.TextField()
    action = models.TextField()
    old = models.JSONField(blank=True, null=True)
    new = models.JSONField(blank=True, null=True)
    by = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    deleted_lead_id = models.TextField(blank=True, null=True)


class DealHistoryModel(models.Model):
    deal_id = models.ForeignKey(T02DL10, on_delete=models.CASCADE, blank=True, null=True)
    timestamp = models.DateTimeField()
    detail = models.TextField()
    action = models.TextField()
    old = models.JSONField(blank=True, null=True)
    new = models.JSONField(blank=True, null=True)
    by = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    deleted_deal_id = models.TextField(blank=True, null=True)


class LeadAssignedReportModel(models.Model):
    lead = models.ForeignKey(T02Led10, on_delete=models.CASCADE, blank=True, null=True)
    assigned_via_rotation = models.BooleanField(null=True, blank=True)
    assigned_manually = models.BooleanField(null=True, blank=True)
    assigned_to = models.ForeignKey(T01Slm10, on_delete=models.CASCADE, blank=True, null=True)
    timestamp = models.DateTimeField(null=True, blank=True)
