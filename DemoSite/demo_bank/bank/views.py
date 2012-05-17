from django.utils import simplejson as json
from django.http import HttpResponse
from django.shortcuts import render_to_response, get_object_or_404, get_list_or_404	

def index(request):
	return render_to_response('bank/index.html')
	
def getuser(request):
	firstname = request.GET['firstname']
	lastname = request.GET['lastname']
	verifiable = request.GET['verifiable']
	response_data = {'message' : "Failure"}
	if verifiable:	
		member = get_object_or_404(VerifiableMember, lastname=lastname, firstname=firstname)
		response_data['message'] = "Success"
		response_data['balance'] = member.balance
	else:
		member = get_object_or_404(Member, lastname=lastname, firstname=firstname)
		response_data['message'] = "Success"
		response_data['balance'] = member.balance
	return HttpResponse(json.dumps(response_data), mimetype="application/json")
		

def lessthan(request):
	balance = request.GET['balance']
	verifiable = request.GET['verifiable']
	response_data = { 'message' : "Failure" }
	if verifiable:
		#queryset = VerifiableMember.objects.filter(balance__lt=4)
		less = get_list_or_404(VerifialbeMember, balance__lt=balance)
		response_data['message'] = "Success"
		response_data['queryset'] = less
	else:
		#queryset = Member.objects.filter(balance__gt=4)
		less = get_list_or_404(VerifialbeMember, balance__lt=balance)
		response_data['message'] = "Success"
		response_data['queryset'] = less
	#return render_to_response('bank/template.html', { 'less' : less })
	return HttpResponse(json.dumps(response_data), mimetype="application/json")
		
def greaterthan(request):
	balance = request.GET['balance']
	verifiable = request.GET['verifiable']
	response_data = { 'message' : "Failure" }
	if verifiable:
		#queryset = VerifiableMember.objects.filter(balance__gt=4)
		greater = get_list_or_404(VerifialbeMember, balance__lt=balance)
		response_data['message'] = "Success"
		response_data['queryset'] = greater
	else:
		#queryset = Member.objects.filter(balance__gt=4)
		greater = get_list_or_404(Member, balance__lt=balance)
		response_data['message'] = "Success"
		response_data['queryset'] = greater
	
	return render_to_response('bank/template.html', { 'greater' : greater })
		
def updateuser(request):
	firstname = request.POST['firstname']
	lastname = request.POST['lastname']
	balance = request.POST['balance']
	verifiable = request.POST['verifiable']
	response_data = { 'message' : "Failure" }
	if verifiable:
		try:
			VerifiableMember.objects.filter(lastname=lastname, firstname=firstname).update(balance=balance)
			response_data['message'] = "Success"
			response_data['balance'] = balance
		except VerifiableMember.DoesNotExist:
			VerifiableMember.objects.create(firstname=firstname, lastname=lastname, balance=balance).save()
			#do something here
	else:
		try:
			Member.objects.filter(lastname=lastname, firstname=firstname).update(balance=balance)
			response_data['message'] = "Success"
			response_data['balance'] = balance
		except Member.DoesNotExist:
			Member.objects.create(firstname=firstname, lastname=lastname, balance=balance).save()
			
			#do something here
	return HttpResponse(json.dumps(response_data), mimetype="application/json")
		
def deleteuser(request):
	firstname = request.POST['firstname']
	lastname = request.POST['lastname']
	verifiable = request.POST['verifiable']
	response_data = { 'message' : "Failure" }
	if verifiable:
		#VerifiableMember.objects.filter(firstname=firstname, lastname=lastname).delete()
		get_object_or_404(VerifiableMember, firstname=firstname, lastname=lastname).delete()
		response_data['message'] = "Success"
	else:
		#Member.objects.filter(firstname=firstname, lastname=lastname).delete()
		get_object_or_404(Member, firstname=firstname, lastname=lastname).delete()
		response_data['message'] = "Success"
		
	return HttpResponse(json.dumps(response_data), mimetype="application/json")
		