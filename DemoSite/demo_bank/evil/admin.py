from evil.models import Member
from django.contrib import admin


class MemberAdmin(admin.ModelAdmin):
	list_filter = ['first_name', 'last_name', 'balance']
	search_fields = ['first_name', 'last_name', 'balance']
	

admin.site.register(Member, MemberAdmin)
	