from django.db import models


class T01Nat10(models.Model):  # nationality, used in esAccounts, esEM, esFP, esIS, esPR
    nationality = models.CharField(db_column="sNatEng", max_length=50)

    class Meta:
        db_table = "T01NAT10"
        ordering = ["nationality"]
        verbose_name = "a7.Nationality Master"

    def __str__(self) -> str:
        return self.nationality



