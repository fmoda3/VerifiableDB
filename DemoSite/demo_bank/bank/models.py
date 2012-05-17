from django.db import models
import VerifiableObject.models as verifiable
# Create your models here.
class VerifiableMember(verifiable.VerifiableModel):
	verifiableId = "VerifiableMember"
	
	first_name = verifiable.VerifiableCharField("first_name", False, max_length=30)
	
	last_name = verifiable.VerifiableCharField("last_name", False, max_length=30)
	 
	balance = verifiable.VerifiableIntegerField("balance", False, max_length=1024)
	
	_first_name_HASH = models.CharField(max_length=1024, blank=True, null=True)
	_first_name_PREV = models.CharField(max_length=1024, blank=True, null=True)
	_first_name_NEXT = models.CharField(max_length=1024, blank=True, null=True)
	
	_last_name_HASH = models.CharField(max_length=1024, blank=True, null=True)
	_last_name_PREV = models.CharField(max_length=1024, blank=True, null=True)
	_last_name_NEXT = models.CharField(max_length=1024, blank=True, null=True)
	
	_balance_HASH = models.CharField(max_length=1024, blank=True, null=True)
	_balance_PREV = models.CharField(max_length=1024, blank=True, null=True)
	_balance_NEXT = models.CharField(max_length=1024, blank=True, null=True)
	
	def __unicode__(self):
		return self.first_name + " " + self.last_name
		
	class Meta:
		db_table = 'best_name_c'
		

