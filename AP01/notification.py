import base64
import os
import random
import uuid
from datetime import timedelta
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import EmailMultiAlternatives
from django.core.mail.backends.smtp import EmailBackend
from django.utils import timezone

from AP01.models.core import User, T01Cfg10


def send_otp(user: User, otp_method: str) -> None:
    otp = random.randint(100000, 999999)

    if otp_method == "email":
        try:
            if user.email:
                subject = "OTP Token"
                message = f"OTP: {otp}"
                recipient_list = [
                    user.email,
                ]

                # Save OTP to User model
                expire_at = timezone.now() + timedelta(minutes=5)
                User.objects.filter(id=user.id).update(otp=otp, otp_expire_at=expire_at)

                # Send Email to user
                send_email(subject, message, recipient_list)
        except Exception as err:
            raise ValueError(err)

    elif otp_method == "voice_call":
        pass

    elif otp_method == "sms":
        pass

    elif otp_method == "reset_password":
        try:
            if user.email:
                subject = "Password Reset OTP"
                message = f"Your OTP for password reset is: {otp}"
                recipient_list = [
                    user.email,
                ]

                # Save OTP to User model
                expire_at = timezone.now() + timedelta(minutes=5)
                User.objects.filter(id=user.id).update(otp=otp, otp_expire_at=expire_at)

                # Send Email to user
                send_email(subject, message, recipient_list)
        except Exception as err:
            raise ValueError(err)

    elif otp_method == "reset_password":
        subject = "Password Reset OTP"
        message = f"Your OTP for password reset is: {otp}"
        recipient_list = [user.email]

        # Save OTP to User model
        expire_at = timezone.now() + timedelta(minutes=5)
        User.objects.filter(id=user.id).update(otp=otp, otp_expire_at=expire_at)

        # Send Email to user
        send_email(subject, message, recipient_list)


""" Send email function """


def send_email(subject, message, mail_to, mail_from=None, attachment=None):
    try:

        config_obj = T01Cfg10.objects.filter().first()

        backend = EmailBackend(
            host=settings.EMAIL_HOST,
            port=settings.EMAIL_PORT,
            username=config_obj.email_sender,
            password=config_obj.password_sender,
            use_tls=settings.EMAIL_USE_TLS,
            fail_silently=False,
        )

        if mail_from is None:
            mail_from = config_obj.email_sender

        # Instantiate the email object with the text version
        email = EmailMultiAlternatives(
            subject,
            message,  # This would be the text version of the email
            mail_from,
            mail_to,
            connection=backend
        )

        # Add the HTML version. This could be the same message if it's already HTML
        email.attach_alternative(message, "text/html")

        if attachment:
            email.attach_file(attachment)

        email.send()

        return True
    except Exception as err:
        print(err)
        raise ValueError(err)


def convert_and_save_b64image(b64_string):
    format, imgstr = b64_string.split(';base64,')
    ext = format.split('/')[-1]

    # create a unique file name
    file_name = '{}.{}'.format(uuid.uuid4(), ext)
    data = ContentFile(base64.b64decode(imgstr), name=file_name)

    # save file
    file_path = os.path.join(settings.MEDIA_ROOT, 'email_images', file_name)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'wb') as f:
        f.write(data.read())

    url = os.path.join(settings.MEDIA_URL, 'email_images', file_name)
    return settings.HOST + url  # assuming you have HOST defined in your settings


def send_email_formatted(subject, message, mail_to, mail_from=None, attachment=None):
    try:

        config_obj = T01Cfg10.objects.filter().first()

        backend = EmailBackend(
            host=settings.EMAIL_HOST,
            port=settings.EMAIL_PORT,
            username=config_obj.email_sender,
            password=config_obj.password_sender,
            use_tls=settings.EMAIL_USE_TLS,
            fail_silently=False,
        )

        if mail_from is None:
            mail_from = config_obj.email_sender

        # Instantiate the email object with the text version
        email = EmailMultiAlternatives(
            subject,
            message,  # This would be the text version of the email
            mail_from,
            mail_to,
            connection=backend
        )

        # Add the HTML version. This could be the same message if it's already HTML
        email.attach_alternative(message, "text/html")

        if attachment:
            email.attach_file(attachment)

        email.send()

        return True
    except Exception as err:
        print(err)
        raise ValueError(err)
