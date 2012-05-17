from django.db import models
import VerifiableObject.models as verifiable

class Person(verifiable.VerifiableModel):
    verifiableId = "Person"
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    
class Car(verifiable.VerifiableModel):
    verifiableId = "Car"
    
    car_make = verifiable.VerifiableCharField("car_make", False, max_length=30)
    _car_make_HASH = models.CharField(max_length=32)
    _car_make_PREV = models.IntegerField(db_index=True, null=True)
    _car_make_NEXT = models.IntegerField(db_index=True, null=True)
    
    car_model = verifiable.VerifiableCharField("car_model", False, max_length=30)
    _car_model_HASH = models.CharField(max_length=32)
    _car_model_PREV = models.IntegerField(db_index=True, null=True)
    _car_model_NEXT = models.IntegerField(db_index=True, null=True)
    
class Dog(verifiable.VerifiableModel):
    verifiableId = "Dog"
    color = verifiable.VerifiableCharField("color", max_length=30)
    breed = verifiable.VerifiableCharField("breed", max_length=30)
    
class BenchmarkModel(models.Model):
    field1 = models.CharField(max_length=30)
    field2 = models.CharField(max_length=30)
    
class BenchmarkIntegrity(verifiable.VerifiableModel):
    verifiableId = "BenchmarkIntegrity"
    field1 = models.CharField(max_length=30)
    field2 = models.CharField(max_length=30)
    
class BenchmarkCompleteness(verifiable.VerifiableModel):
    verifiableId = "BenchmarkCompleteness"
    field1 = verifiable.VerifiableCharField("field1", False, max_length=30)
    _field1_HASH = models.CharField(max_length=32)
    _field1_PREV = models.IntegerField(db_index=True, null=True)
    _field1_NEXT = models.IntegerField(db_index=True, null=True)
    
    field2 = verifiable.VerifiableCharField("field2", False, max_length=30)
    _field2_HASH = models.CharField(max_length=32)
    _field2_PREV = models.IntegerField(db_index=True, null=True)
    _field2_NEXT = models.IntegerField(db_index=True, null=True)
    
class BenchmarkCompletenessAndFreshness(verifiable.VerifiableModel):
    verifiableId = "BenchmarkCompletenessAndFreshness"
    field1 = verifiable.VerifiableCharField("field1", True, max_length=30)
    field2 = verifiable.VerifiableCharField("field2", True, max_length=30)
    