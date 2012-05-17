from django.db import models

# Create your models here.
class Member(models.Model):
	_data_hash = models.CharField(max_length=1024)
	
	first_name = models.CharField(max_length=30)

	
	last_name = models.CharField(max_length=30)
	
	
	balance = models.IntegerField(max_length=1024)
	
	_first_name_HASH = models.CharField(max_length=1024, null=True, blank=True)
	_first_name_PREV = models.CharField(max_length=1024, null=True, blank=True)
	_first_name_NEXT = models.CharField(max_length=1024, null=True, blank=True)
	
	_last_name_HASH = models.CharField(max_length=1024, null=True, blank=True)
	_last_name_PREV = models.CharField(max_length=1024, null=True, blank=True)
	_last_name_NEXT = models.CharField(max_length=1024, null=True, blank=True)
	
	_balance_HASH = models.CharField(max_length=1024, null=True, blank=True)
	_balance_PREV = models.CharField(max_length=1024, null=True, blank=True)
	_balance_NEXT = models.CharField(max_length=1024, null=True, blank=True)
	
	
	
	
	def __unicode__(self):
		return self.first_name + " " + self.last_name
		
	class Meta:
		db_table = 'best_name_c'