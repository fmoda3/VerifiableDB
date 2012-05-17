from django.test import TestCase
from django.db import models
from django.db import connection
from TestObject.models import Person, Car, Dog, BenchmarkModel, BenchmarkIntegrity, BenchmarkCompleteness, BenchmarkCompletenessAndFreshness
from VerifiableObject.models import VerifiableQuerySet, VerifiableEmptyQuerySet, VerifiableModel, VerifiableError
import random
from datetime import datetime

class ObjectIntegrityTestCase(TestCase):
    def setUp(self):
        self.boy = Person.objects.create(first_name="Ben", last_name="Bitdiddle")
        self.girl = Person.objects.create(first_name="Alyssa", last_name="Hacker")

    def test_people_can_be_created(self):
        """Test that our people were created properly"""
        self.assertEqual(self.boy.first_name, 'Ben')
        self.assertEqual(self.boy.last_name, 'Bitdiddle')
        self.assertEqual(self.girl.first_name, 'Alyssa')
        self.assertEqual(self.girl.last_name, 'Hacker')
        self.assertTrue(isinstance(self.girl, VerifiableModel))
        self.assertTrue(isinstance(self.boy, VerifiableModel))

    def test_people_can_be_edited(self):
        """ Make sure that we can edit our objects """
        self.boy.first_name = "John"
        self.girl.first_name = "Eve"
        self.boy.save()
        self.girl.save()
        self.assertEqual(self.boy.first_name, 'John')
        self.assertEqual(self.girl.first_name, 'Eve')

    def test_people_can_be_deleted(self):
        """ Make sure we can delete our objects """
        self.boy.delete()
        q = Person.objects.all()
        self.assertEqual(q.count(), 1)
        self.girl.delete()
        q = Person.objects.all()
        self.assertEqual(q.count(), 0)

class QuerySetIntegrityTestCase(TestCase):
    def setUp(self):
        self.boy = Person.objects.create(first_name="Ben", last_name="Bitdiddle")
        self.girl = Person.objects.create(first_name="Alyssa", last_name="Hacker")
        self.q = Person.objects.get_query_set()

    def test_get_queryset(self):
        """ Make sure that we can get a verifiable query set """
        self.assertEquals(type(self.q), VerifiableQuerySet)

    def test_count_queryset(self):
        """ Make sure we didn't break the count() method """
        self.assertEquals(self.q.count(), 2)

    def test_get_object(self):
        """ Make sure that we can still get an object """
        self.assertEquals(self.q.get(first_name="Ben", last_name="Bitdiddle"), self.boy)
    
    def test_get_or_create_object(self):
        """ Make sure that get or create works correctly """
        (self.notexists, created) = Person.objects.get_or_create(first_name="Louis", last_name="Reasoner")
        self.assertTrue(created)
        (self.notexists, created) = Person.objects.get_or_create(first_name="Ben", last_name="Bitdiddle")
        self.assertFalse(created)

    def test_get_latest(self):
        """ Test the get latest method """
        self.new = Person.objects.create(first_name="Bob", last_name="Hacker")
        self.assertEquals(self.q.latest("first_name"), self.new)
    
    def test_exists(self):
        """ Test exists function """
        exists = self.q.filter(last_name="Bitdiddle").exists()
        self.assertEquals(exists, True)
    
    def test_none(self):
        """ Test none function """
        empty = self.q.none()
        self.assertEquals(type(empty), VerifiableEmptyQuerySet)

    def test_all(self):
        allrows = self.q.all()
        self.assertEquals(type(allrows), VerifiableQuerySet)
        self.assertTrue(allrows.exists())
        count = allrows.count()
        self.assertEquals(count, 2)

    def test_filter(self):
        """ Make sure that filter works """
        new_q = self.q.filter(last_name="Bitdiddle")
        self.assertEquals(new_q[0], self.q.get(last_name="Bitdiddle"))

    def test_update(self):
        """ Make sure that update works """
        self.q.filter(last_name="Bitdiddle").update(first_name="Joe")
        self.q.filter(last_name="Hacker").update(last_name="Haxxor")
        self.assertEquals(self.q.get(last_name="Bitdiddle").first_name, "Joe")
        self.assertEquals(self.q.get(first_name="Alyssa").last_name, "Haxxor")
    
    def test_order_by(self):
        """ Make sure that order by works """
        orderedrows = self.q.order_by("last_name")
        self.assertEquals(type(orderedrows), VerifiableQuerySet)
        self.assertTrue(orderedrows.exists())
        count = orderedrows.count()
        self.assertEquals(count, 2)
    
    #def test_distinct(self):
    #    """ Make sure that distinct works """
    #    distinctrows = self.q.distinct()
    #    self.assertEquals(type(distinctrows), VerifiableQuerySet)
    #    self.assertTrue(distinctrows.exists())
    #    count = distinctrows.count()
    #    self.assertEquals(count, 2)
    
    def test_reverse(self):
        """ Make sure that reverse works """
        reverserows = self.q.reverse()
        self.assertEquals(type(reverserows), VerifiableQuerySet)
        self.assertTrue(reverserows.exists())
        count = reverserows.count()
        self.assertEquals(count, 2)

    def test_exclude(self):
        """ Make sure that exclude works """
        new_q = self.q.exclude(last_name="Bitdiddle")
        self.assertEquals(new_q[0], self.q.get(last_name="Hacker"))

    def test_multiple_calls(self):
        """ Testing multiple calls """
        Person.objects.create(first_name="Ben", last_name="Hacker")
        Person.objects.create(first_name="Alyssa", last_name="Bitdiddle")
        q = Person.objects.get_query_set()
        self.assertEquals(q.filter(first_name="Alyssa").count(), 2)
        self.assertEquals(q.filter(last_name="Bitdiddle").filter(first_name="Ben").count(), 1)
        
    def test_verification_failure(self):
        """ Test for verification error (negative case) """
        bad_object = Person
        bad_object.objects = models.Manager()
        bad_object.objects.contribute_to_class(Person, "person")
        bad_boy = bad_object.objects.get_query_set().filter(last_name="Bitdiddle")
        bad_boy.update(first_name="Joe")
        exception_thrown = False
        try:
            self.q.get(last_name="Bitdiddle").first_name
        except VerifiableError:
            exception_thrown = True
        finally:
            self.assertEquals(exception_thrown, True)
            
class ObjectCompletenessTestCase(TestCase):
    def setUp(self):
        self.ford = Car.objects.create(car_make="Ford", car_model="Escape")
        self.nissan = Car.objects.create(car_make="Nissan", car_model="Rogue")
        self.acura = Car.objects.create(car_make="Acura", car_model="Eclipse")
        
    def test_people_can_be_created(self):
        """Test that our people were created properly"""
        self.assertEqual(self.ford.car_make, 'Ford')
        self.assertEqual(self.ford.car_model, 'Escape')
        self.assertEqual(self.nissan.car_make, 'Nissan')
        self.assertEqual(self.nissan.car_model, 'Rogue')
        self.assertEqual(self.acura.car_make, 'Acura')
        self.assertEqual(self.acura.car_model, 'Eclipse')
        self.assertTrue(isinstance(self.ford, VerifiableModel))
        self.assertTrue(isinstance(self.nissan, VerifiableModel))
        self.assertTrue(isinstance(self.acura, VerifiableModel))
        
    def test_people_can_be_edited(self):
        """ Make sure that we can edit our objects """
        self.ford.car_make = "Honda"
        self.nissan.car_make = "Toyota"
        self.acura.car_make = "GE"
        self.ford.save()
        self.nissan.save()
        self.acura.save()
        self.assertEqual(self.ford.car_make, 'Honda')
        self.assertEqual(self.nissan.car_make, 'Toyota')
        self.assertEqual(self.acura.car_make, 'GE')
        
    def test_cars_can_be_deleted(self):
        """ Make sure we can delete our objects """
        self.ford.delete()
        q = Car.objects.all()
        self.assertEqual(q.count(), 2)
        self.nissan.delete()
        q = Car.objects.all()
        self.assertEqual(q.count(), 1)
        self.acura.delete()
        q = Car.objects.all()
        self.assertEqual(q.count(), 0)

class QuerySetCompletenessTestCase(TestCase):
    def setUp(self):
        self.ford = Car.objects.create(car_make="Ford", car_model="Escape")
        self.nissan = Car.objects.create(car_make="Nissan", car_model="Rogue")
        self.acura = Car.objects.create(car_make="Acura", car_model="Eclipse")
        self.q = Car.objects.get_query_set()
        
    def test_get_queryset(self):
        """ Make sure that we can get a verifiable query set """
        self.assertEquals(type(self.q), VerifiableQuerySet)
        
    def test_count_queryset(self):
        """ Make sure we didn't break the count() method """
        self.assertEquals(self.q.count(), 3)
        
    def test_get_object(self):
        """ Make sure that we can still get an object """
        self.assertEquals(self.q.get(car_make="Ford", car_model="Escape"), self.ford)
        
    def test_get_or_create_object(self):
        """ Make sure that get or create works correctly """
        (self.notexists, created) = Car.objects.get_or_create(car_make="Honda", car_model="Accord")
        self.assertTrue(created)
        (self.notexists, created) = Car.objects.get_or_create(car_make="Ford", car_model="Escape")
        self.assertFalse(created)
        
    def test_get_latest(self):
        """ Test the get latest method """
        self.new = Car.objects.create(car_make="Zipcar", car_model="Accord")
        self.assertEquals(self.q.latest("car_make"), self.new)

    def test_exists(self):
        """ Test exists function """
        exists = self.q.filter(car_model="Escape").exists()
        self.assertEquals(exists, True)

    def test_none(self):
        """ Test none function """
        empty = self.q.none()
        self.assertEquals(type(empty), VerifiableEmptyQuerySet)

    def test_all(self):
        allrows = self.q.all()
        self.assertEquals(type(allrows), VerifiableQuerySet)
        self.assertTrue(allrows.exists())
        count = allrows.count()
        self.assertEquals(count, 3)
        
    def test_filter(self):
        """ Make sure that filter works """
        new_q = self.q.filter(car_make="Ford")
        self.assertEquals(new_q[0], self.q.get(car_make="Ford"))
        
    def test_filter_fail(self):
        """ Make sure that filter can't be applied more than once """
        exception_thrown = False
        try:
            self.q.filter(car_model="Escape").filter(car_make="Ford")
        except VerifiableError:
            exception_thrown = True
        finally:
            self.assertEquals(exception_thrown, True)

    def test_update(self):
        """ Make sure that update works """
        Car.objects.get_query_set().filter(car_make="Ford").update(car_model="Mustang")
        Car.objects.get_query_set().filter(car_model="Rogue").update(car_make="Toyota")
        self.assertEquals(self.q.get(car_make="Ford").car_model, "Mustang")
        self.assertEquals(self.q.get(car_model="Rogue").car_make, "Toyota")
        
    def test_order_by(self):
        """ Make sure that order by works """
        orderedrows = self.q.order_by("car_make")
        self.assertEquals(type(orderedrows), VerifiableQuerySet)
        self.assertTrue(orderedrows.exists())
        count = orderedrows.count()
        self.assertEquals(count, 3)

    #def test_distinct(self):
    #    """ Make sure that distinct works """
    #    distinctrows = self.q.distinct()
    #    self.assertEquals(type(distinctrows), VerifiableQuerySet)
    #    self.assertTrue(distinctrows.exists())
    #    count = distinctrows.count()
    #    self.assertEquals(count, 3)

    def test_reverse(self):
        """ Make sure that reverse works """
        reverserows = self.q.reverse()
        self.assertEquals(type(reverserows), VerifiableQuerySet)
        self.assertTrue(reverserows.exists())
        count = reverserows.count()
        self.assertEquals(count, 3)

    def test_exclude(self):
        """ Make sure that exclude works """
        new_q = self.q.exclude(car_make__lt="Ford")
        self.assertEquals(new_q[0], self.q.get(car_make="Ford"))
        
    def test_exclude_fail(self):
        """ Make sure that exclude can't be applied more than once """
        exception_thrown = False
        try:
            self.q.exclude(car_model__lt="Escape").exclude(car_make__gt="Ford")
        except VerifiableError:
            exception_thrown = True
        finally:
            self.assertEquals(exception_thrown, True)

    def test_multiple_calls(self):
        """ Testing multiple calls """
        Car.objects.create(car_make="Ford", car_model="Coupe")
        Car.objects.create(car_make="Nissan", car_model="Escape")
        q = Car.objects.get_query_set()
        self.assertEquals(q.filter(car_make="Nissan").count(), 2)
        self.assertEquals(q.filter(car_model="Escape").count(), 2)
        
    def test_verification_failure(self):
        """ Test for verification error (negative case) """
        bad_object = Car
        bad_object.objects = models.Manager()
        bad_object.objects.contribute_to_class(Car, "car")
        bad_ford = bad_object.objects.get_query_set().filter(car_model="Escape")
        bad_ford.update(car_make="Honda")
        exception_thrown = False
        try:
            self.q.get(car_model="Escape").car_make
        except VerifiableError:
            exception_thrown = True
        finally:
            self.assertEquals(exception_thrown, True)
            
class ObjectCompletenessFreshnessTestCase(TestCase):
    def setUp(self):
        # we have to do this to make that our auxiliary data structure is empty
        for f in Dog._meta.local_fields:
            if hasattr(f.__class__, '_tree'):
                t = f._tree
                c = t.conn.cursor()

                c.execute("DELETE FROM %s WHERE 1" % t.table_name)
                t.conn.commit()

                t.root = None
                t.cache = {}
                t.counter = 0
                t.bump_root()

        self.lab = Dog.objects.create(color="Brown", breed="Labrador")
        self.bull = Dog.objects.create(color="Black", breed="Bulldog")
        self.terr = Dog.objects.create(color="White", breed="Terrier")

    def test_dogs_can_be_created(self):
        """Test that our people were created properly"""
        self.assertEqual(self.lab.color, 'Brown')
        self.assertEqual(self.lab.breed, 'Labrador')
        self.assertEqual(self.bull.color, 'Black')
        self.assertEqual(self.bull.breed, 'Bulldog')
        self.assertEqual(self.terr.color, 'White')
        self.assertEqual(self.terr.breed, 'Terrier')
        self.assertTrue(isinstance(self.lab, VerifiableModel))
        self.assertTrue(isinstance(self.bull, VerifiableModel))
        self.assertTrue(isinstance(self.terr, VerifiableModel))

    def test_dogs_can_be_edited(self):
        """ Make sure that we can edit our objects """
        self.lab.color = "Blue"
        self.bull.color = "Brown"
        self.terr.color = "Tan"
        self.lab.save()
        self.bull.save()
        self.terr.save()
        self.assertEqual(self.lab.color, 'Blue')
        self.assertEqual(self.bull.color, 'Brown')
        self.assertEqual(self.terr.color, 'Tan')

    def test_dogs_can_be_deleted(self):
        """ Make sure we can delete our objects """
        self.lab.delete()
        q = Dog.objects.all()
        self.assertEqual(q.count(), 2)
        self.bull.delete()
        q = Dog.objects.all()
        self.assertEqual(q.count(), 1)
        self.terr.delete()
        q = Dog.objects.all()
        self.assertEqual(q.count(), 0)
        
class QuerySetCompletenessFreshnessTestCase(TestCase):
    def setUp(self):
        # we have to do this to make that our auxiliary data structure is empty
        for f in Dog._meta.local_fields:
            if hasattr(f.__class__, '_tree'):
                t = f._tree
                c = t.conn.cursor()

                c.execute("DELETE FROM %s WHERE 1" % t.table_name)
                t.conn.commit()

                t.root = None
                t.cache = {}
                t.counter = 0
                t.bump_root()

        self.lab = Dog.objects.create(color="Brown", breed="Labrador")
        self.bull = Dog.objects.create(color="Black", breed="Bulldog")
        self.terr = Dog.objects.create(color="White", breed="Terrier")
        self.q = Dog.objects.get_query_set()

    def test_get_queryset(self):
        """ Make sure that we can get a verifiable query set """
        self.assertEquals(type(self.q), VerifiableQuerySet)

    def test_count_queryset(self):
        """ Make sure we didn't break the count() method """
        self.assertEquals(self.q.count(), 3)

    def test_get_object(self):
        """ Make sure that we can still get an object """
        self.assertEquals(self.q.get(color="Brown", breed="Labrador"), self.lab)

    def test_get_or_create_object(self):
        """ Make sure that get or create works correctly """
        (self.notexists, created) = Dog.objects.get_or_create(color="Yellow", breed="Hotdog")
        self.assertTrue(created)
        (self.notexists, created) = Dog.objects.get_or_create(color="Brown", breed="Labrador")
        self.assertFalse(created)

    def test_get_latest(self):
        """ Test the get latest method """
        self.new = Dog.objects.create(color="Zippy", breed="Hotdog")
        self.assertEquals(self.q.latest("color"), self.new)

    def test_exists(self):
        """ Test exists function """
        exists = self.q.filter(breed="Labrador").exists()
        self.assertEquals(exists, True)

    def test_none(self):
        """ Test none function """
        empty = self.q.none()
        self.assertEquals(type(empty), VerifiableEmptyQuerySet)

    def test_all(self):
        allrows = self.q.all()
        self.assertEquals(type(allrows), VerifiableQuerySet)
        self.assertTrue(allrows.exists())
        count = allrows.count()
        self.assertEquals(count, 3)
        
    def test_filter(self):
        """ Make sure that filter works """
        new_q = self.q.filter(color="Brown")
        self.assertEquals(new_q[0], self.q.get(color="Brown"))

    def test_filter_fail(self):
        """ Make sure that filter can't be applied more than once """
        exception_thrown = False
        try:
            self.q.filter(breed="Labrador").filter(color="Brown")
        except VerifiableError:
            exception_thrown = True
        finally:
            self.assertEquals(exception_thrown, True)

    def test_update(self):
        """ Make sure that update works """
        Dog.objects.get_query_set().filter(color="Brown").update(breed="Hotdog")
        Dog.objects.get_query_set().filter(breed="Bulldog").update(color="Yellow")
        self.assertEquals(self.q.get(color="Brown").breed, "Hotdog")
        self.assertEquals(self.q.get(breed="Bulldog").color, "Yellow")

    def test_order_by(self):
        """ Make sure that order by works """
        orderedrows = self.q.order_by("color")
        self.assertEquals(type(orderedrows), VerifiableQuerySet)
        self.assertTrue(orderedrows.exists())
        count = orderedrows.count()
        self.assertEquals(count, 3)

    #def test_distinct(self):
    #    """ Make sure that distinct works """
    #    distinctrows = self.q.distinct()
    #    self.assertEquals(type(distinctrows), VerifiableQuerySet)
    #    self.assertTrue(distinctrows.exists())
    #    count = distinctrows.count()
    #    self.assertEquals(count, 3)

    def test_reverse(self):
        """ Make sure that reverse works """
        reverserows = self.q.reverse()
        self.assertEquals(type(reverserows), VerifiableQuerySet)
        self.assertTrue(reverserows.exists())
        count = reverserows.count()
        self.assertEquals(count, 3)

    def test_exclude(self):
        """ Make sure that exclude works """
        new_q = self.q.exclude(color__lt="Brown")
        self.assertEquals(new_q[0], self.q.get(color="Brown"))

    def test_exclude_fail(self):
        """ Make sure that exclude can't be applied more than once """
        exception_thrown = False
        try:
            self.q.exclude(breed__lt="Labrador").exclude(color__gt="Brown")
        except VerifiableError:
            exception_thrown = True
        finally:
            self.assertEquals(exception_thrown, True)

    def test_multiple_calls(self):
        """ Testing multiple calls """
        Dog.objects.create(color="Brown", breed="Puppy")
        Dog.objects.create(color="Orange", breed="Labrador")
        q = Dog.objects.get_query_set()
        self.assertEquals(q.filter(color="Brown").count(), 2)
        self.assertEquals(q.filter(breed="Labrador").count(), 2)

    def test_verification_failure(self):
        """ Test for verification error (negative case) """
        bad_object = Dog
        bad_object.objects = models.Manager()
        bad_object.objects.contribute_to_class(Dog, "dog")
        bad_dog = bad_object.objects.get_query_set().filter(breed="Labrador")
        bad_dog.update(color="Yellow")
        exception_thrown = False
        try:
            self.q.get(breed="Labrador").color
        except VerifiableError:
            exception_thrown = True
        finally:
            self.assertEquals(exception_thrown, True)

count = 10
class BenchmarkModelTestCase(TestCase):
    def test_benchmark(self):
        print ""
        print "Testing Basic Django Models"
        start = datetime.now()
        for i in range(count):
            r = random.randrange(0,3)
            if r == 0:
                BenchmarkModel.objects.create(field1="Ford", field2="Escape")
            if r == 1:
                BenchmarkModel.objects.create(field1="Nissan", field2="Rogue")
            if r == 2:
                BenchmarkModel.objects.create(field1="Acura", field2="Eclipse")
        end = datetime.now()
        duration = end - start
        print str(count) + " inserts took : " + str(duration) + " seconds"
        print "    inserts per second: " + str(count/duration.total_seconds())
        
        BenchmarkModel.objects.create(field1="Mercedes", field2="Convertible")

        start = datetime.now()
        for i in range(count):
            c = BenchmarkModel.objects.get_query_set().filter(field1="Mercedes")
            for r in c:
                continue
        end = datetime.now()
        duration = end - start
        print str(count) + " point queries took : " + str(duration) + " seconds"
        print "    point queries per second: " + str(count/duration.total_seconds())
        
        BenchmarkModel.objects.get(field1="Mercedes").delete()
        
        start = datetime.now()
        for i in range(count):
            c = BenchmarkModel.objects.get_query_set().filter(field1__lte="Ford")
            for r in c:
                continue
        end = datetime.now()
        duration = end - start
        print str(count) + " half range queries took : " + str(duration) + " seconds"
        print "    half range queries per second: " + str(count/duration.total_seconds())
        
        start = datetime.now()
        for i in range(count):
            c = BenchmarkModel.objects.get_query_set().filter(field1__range=("BMW","Honda"))
            for r in c:
                continue
        end = datetime.now()
        duration = end - start
        print str(count) + " full range queries took : " + str(duration) + " seconds"
        print "    full range queries per second: " + str(count/duration.total_seconds())
        
        start = datetime.now()
        for i in range(count):
            r = random.randrange(0,2)
            if r == 0:
                BenchmarkModel.objects.get_query_set().filter(id__exact=i+1).update(field1="Honda")
            if r == 1:
                BenchmarkModel.objects.get_query_set().filter(id__exact=i+1).update(field2="Accord")
        end = datetime.now()
        duration = end - start
        print str(count) + " updates took : " + str(duration) + " seconds"
        print "    updates per second: " + str(count/duration.total_seconds())
        
        start = datetime.now()
        for i in range(count):
            BenchmarkModel.objects.get_query_set().get(id__exact=i+1).delete()
        end = datetime.now()
        duration = end - start
        print str(count) + " deletes took : " + str(duration) + " seconds"
        print "    deletes per second: " + str(count/duration.total_seconds())
        
class BenchmarkIntegrityTestCase(TestCase):
    def test_benchmark(self):
        print ""
        print "Testing Models with Integrity"
        start = datetime.now()
        for i in range(count):
            r = random.randrange(0,3)
            if r == 0:
                BenchmarkIntegrity.objects.create(field1="Ford", field2="Escape")
            if r == 1:
                BenchmarkIntegrity.objects.create(field1="Nissan", field2="Rogue")
            if r == 2:
                BenchmarkIntegrity.objects.create(field1="Acura", field2="Eclipse")
        end = datetime.now()
        duration = end - start
        print str(count) + " inserts took : " + str(duration) + " seconds"
        print "    inserts per second: " + str(count/duration.total_seconds())

        BenchmarkIntegrity.objects.create(field1="Mercedes", field2="Convertible")

        start = datetime.now()
        for i in range(count):
            c = BenchmarkIntegrity.objects.get_query_set().filter(field1="Mercedes")
            for r in c:
                continue
        end = datetime.now()
        duration = end - start
        print str(count) + " point queries took : " + str(duration) + " seconds"
        print "    point queries per second: " + str(count/duration.total_seconds())
        
        BenchmarkIntegrity.objects.get(field1="Mercedes").delete()

        start = datetime.now()
        for i in range(count):
            c = BenchmarkIntegrity.objects.get_query_set().filter(field1__lte="Ford")
            for r in c:
                continue
        end = datetime.now()
        duration = end - start
        print str(count) + " half range queries took : " + str(duration) + " seconds"
        print "    half range queries per second: " + str(count/duration.total_seconds())

        start = datetime.now()
        for i in range(count):
            c = BenchmarkIntegrity.objects.get_query_set().filter(field1__range=("BMW","Honda"))
            for r in c:
                continue
        end = datetime.now()
        duration = end - start
        print str(count) + " full range queries took : " + str(duration) + " seconds"
        print "    full range queries per second: " + str(count/duration.total_seconds())

        start = datetime.now()
        for i in range(count):
            r = random.randrange(0,2)
            if r == 0:
                BenchmarkIntegrity.objects.get_query_set().filter(id__exact=i+1).update(field1="Honda")
            if r == 1:
                BenchmarkIntegrity.objects.get_query_set().filter(id__exact=i+1).update(field2="Accord")
        end = datetime.now()
        duration = end - start
        print str(count) + " updates took : " + str(duration) + " seconds"
        print "    updates per second: " + str(count/duration.total_seconds())
        
        start = datetime.now()
        for i in range(count):
            BenchmarkIntegrity.objects.get_query_set().get(id__exact=i+1).delete()
        end = datetime.now()
        duration = end - start
        print str(count) + " deletes took : " + str(duration) + " seconds"
        print "    deletes per second: " + str(count/duration.total_seconds())
              
class BenchmarkCompletenessTestCase(TestCase):
    def test_benchmark(self):
        import os # make sure local storage for roots does not exist
        if os.path.exists("verifiable.sqlite"):
            os.remove("verifiable.sqlite")

        print ""
        print "Testing Models with Integrity and Completeness"
        start = datetime.now()
        for i in range(count):
            r = random.randrange(0,3)
            if r == 0:
                BenchmarkCompleteness.objects.create(field1="Ford", field2="Escape")
            if r == 1:
                BenchmarkCompleteness.objects.create(field1="Nissan", field2="Rogue")
            if r == 2:
                BenchmarkCompleteness.objects.create(field1="Acura", field2="Eclipse")
        end = datetime.now()
        duration = end - start
        print str(count) + " inserts took : " + str(duration) + " seconds"
        print "    inserts per second: " + str(count/duration.total_seconds())
        
        rows = BenchmarkCompleteness.objects.get_query_set().all()

        BenchmarkCompleteness.objects.create(field1="Mercedes", field2="Convertible")

        start = datetime.now()
        for i in range(count):
            BenchmarkCompleteness.objects.get_query_set().filter(field1="Mercedes")
        end = datetime.now()
        duration = end - start
        print str(count) + " point queries took : " + str(duration) + " seconds"
        print "    point queries per second: " + str(count/duration.total_seconds())
        
        BenchmarkCompleteness.objects.get(field1="Mercedes").delete()
        
        rows = BenchmarkCompleteness.objects.get_query_set().all()

        start = datetime.now()
        for i in range(count):
            BenchmarkCompleteness.objects.get_query_set().filter(field1__lte="BMW")
        end = datetime.now()
        duration = end - start
        print str(count) + " half range queries took : " + str(duration) + " seconds"
        print "    half range queries per second: " + str(count/duration.total_seconds())
        
        rows = BenchmarkCompleteness.objects.get_query_set().all()

        start = datetime.now()
        for i in range(count):
            BenchmarkCompleteness.objects.get_query_set().filter(field1__range=("BMW","Honda"))
        end = datetime.now()
        duration = end - start
        print str(count) + " full range queries took : " + str(duration) + " seconds"
        print "    full range queries per second: " + str(count/duration.total_seconds())
        
        rows = BenchmarkCompleteness.objects.get_query_set().all()
        
        start = datetime.now()
        for i in range(count):
            r = random.randrange(0,2)
            if r == 0:
                BenchmarkCompleteness.objects.get_query_set().filter(id__exact=i+1).update(field1="Honda")
            if r == 1:
                BenchmarkCompleteness.objects.get_query_set().filter(id__exact=i+1).update(field2="Accord")
        end = datetime.now()
        duration = end - start
        print str(count) + " updates took : " + str(duration) + " seconds"
        print "    updates per second: " + str(count/duration.total_seconds())
        
        rows = BenchmarkCompleteness.objects.get_query_set().all()
        
        start = datetime.now()
        for i in range(count):
            rows[i].delete()
        end = datetime.now()
        duration = end - start
        print str(count) + " deletes took : " + str(duration) + " seconds"
        print "    deletes per second: " + str(count/duration.total_seconds())

class BenchmarkCompletenessFreshnessTestCase(TestCase):
    def test_benchmark(self):
        print ""
        print "Testing Models with Integrity, Completeness, and Freshness"
        start = datetime.now()
        for i in range(count):
            r = random.randrange(0,3)
            if r == 0:
                BenchmarkCompletenessAndFreshness.objects.create(field1="Ford", field2="Escape")
            if r == 1:
                BenchmarkCompletenessAndFreshness.objects.create(field1="Nissan", field2="Rogue")
            if r == 2:
                BenchmarkCompletenessAndFreshness.objects.create(field1="Acura", field2="Eclipse")
        end = datetime.now()
        duration = end - start
        print str(count) + " inserts took : " + str(duration) + " seconds"
        print "    inserts per second: " + str(count/duration.total_seconds())

        rows = BenchmarkCompletenessAndFreshness.objects.get_query_set().all()

        BenchmarkCompletenessAndFreshness.objects.create(field1="Mercedes", field2="Convertible")

        start = datetime.now()
        for i in range(count):
            BenchmarkCompletenessAndFreshness.objects.get_query_set().filter(field1="Mercedes")
        end = datetime.now()
        duration = end - start
        print str(count) + " point queries took : " + str(duration) + " seconds"
        print "    point queries per second: " + str(count/duration.total_seconds())

        BenchmarkCompletenessAndFreshness.objects.get(field1="Mercedes").delete()

        rows = BenchmarkCompletenessAndFreshness.objects.get_query_set().all()

        start = datetime.now()
        for i in range(count):
            BenchmarkCompletenessAndFreshness.objects.get_query_set().filter(field1__lte="BMW")
        end = datetime.now()
        duration = end - start
        print str(count) + " half range queries took : " + str(duration) + " seconds"
        print "    half range queries per second: " + str(count/duration.total_seconds())

        rows = BenchmarkCompletenessAndFreshness.objects.get_query_set().all()

        start = datetime.now()
        for i in range(count):
            BenchmarkCompletenessAndFreshness.objects.get_query_set().filter(field1__range=("BMW","Honda"))
        end = datetime.now()
        duration = end - start
        print str(count) + " full range queries took : " + str(duration) + " seconds"
        print "    full range queries per second: " + str(count/duration.total_seconds())

        rows = BenchmarkCompletenessAndFreshness.objects.get_query_set().all()

        start = datetime.now()
        for i in range(count):
            r = random.randrange(0,2)
            if r == 0:
                BenchmarkCompletenessAndFreshness.objects.get_query_set().filter(id__exact=i+1).update(field1="Honda")
            if r == 1:
                BenchmarkCompletenessAndFreshness.objects.get_query_set().filter(id__exact=i+1).update(field2="Accord")
        end = datetime.now()
        duration = end - start
        print str(count) + " updates took : " + str(duration) + " seconds"
        print "    updates per second: " + str(count/duration.total_seconds())

        rows = BenchmarkCompletenessAndFreshness.objects.get_query_set().all()

        start = datetime.now()
        for i in range(count):
            rows[i].delete()
        end = datetime.now()
        duration = end - start
        print str(count) + " deletes took : " + str(duration) + " seconds"
        print "    deletes per second: " + str(count/duration.total_seconds())
