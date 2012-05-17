from bank.models import VerifiableMember
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

class HighMidLowFilter(admin.SimpleListFilter):
	title = _('Approximate Balance')
	
	parameter_name = 'range'
	
	def lookups(self, request, model_admin):
		return (
			('high', _('Greater than 1,000,000')),
			('mid', _('Between 0 and 1,000,000')),
			('low', _('Less than 0 (broke)'))
		)
		
	def queryset(self, request, queryset):
		if self.value() == 'high':
			return queryset.filter(balance__gt=1000000)
		if self.value() == 'mid':
			return queryset.filter(balance__range=(0, 1000000))
		if self.value() == 'low':
			return queryset.filter(balance__lt=0)
class LastNameFilter(admin.SimpleListFilter):
	title = _('Last Name Half')
	
	parameter_name = 'half'
	
	def lookups(self, request, model_admin):
		return (
			('first', _('A - M')),
			('second', _('N - Z'))
		)
		
	def queryset(self, request, queryset):
		if self.value() == 'first':
			return queryset.filter(first_name__lte='M')
		if self.value() == 'second':
			return queryset.filter(last_name__gte='N')
		
class VerifiableMemberAdmin(admin.ModelAdmin):
	list_filter = ['first_name', 'last_name', HighMidLowFilter, LastNameFilter]
	exclude = ['_first_name_HASH', '_first_name_PREV', '_first_name_NEXT', '_last_name_HASH', '_last_name_PREV', '_last_name_NEXT', '_balance_HASH', '_balance_PREV', '_balance_NEXT']
	def save_model(self, request, obj, form, change):
		if change:
			obj.save()
		else:
			#print form
			#print request 
			print change
			print obj
			VerifiableMember.objects.create(first_name=obj.first_name, last_name=obj.last_name, balance=obj.balance)
			
admin.site.register(VerifiableMember, VerifiableMemberAdmin)