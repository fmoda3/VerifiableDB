from django.db import models
import hashlib  # Going to be used for hashing in the hash tree
import hmac     # Going to be used for tuple macing

# Manager methods here: https://code.djangoproject.com/browser/django/trunk/django/db/models/manager.py
# Manager handles the queries.  Often reached by calling Model.objects.  So, overriding objects with this manager in VerifiableModel.
class VerifiableManager(models.Manager):
    # Returns query sets
    def get_empty_query_set(self):
        # Do we want to prevent them from using arbitrary queries?
        return null;
        
    def get_query_set(self):
        # Do we want to prevent them from using arbitrary queries?
        return null;
        
    # Need to implement checks for these getters
    # Which ones should we just outright prevent?
    def none(self):
        return super(VerifiableManager, self).get_empty_query_set()
        
    def all(self):
        return super(VerifiableManager, self).get_query_set()
        
    def count(self):
        return super(VerifiableManager, self).get_query_set().count()

    def dates(self, *args, **kwargs):
        return super(VerifiableManager, self).get_query_set().dates(*args, **kwargs)

    def distinct(self, *args, **kwargs):
        return super(VerifiableManager, self).get_query_set().distinct(*args, **kwargs)

    def extra(self, *args, **kwargs):
        return super(VerifiableManager, self).get_query_set().extra(*args, **kwargs)

    def get(self, *args, **kwargs):
        return super(VerifiableManager, self)get_query_set().get(*args, **kwargs)

    def get_or_create(self, **kwargs):
        return super(VerifiableManager, self).get_query_set().get_or_create(**kwargs)

    def create(self, **kwargs):
        return super(VerifiableManager, self).get_query_set().create(**kwargs)

    def bulk_create(self, *args, **kwargs):
        return super(VerifiableManager, self).get_query_set().bulk_create(*args, **kwargs)

    def filter(self, *args, **kwargs):
        return super(VerifiableManager, self).get_query_set().filter(*args, **kwargs)

    def aggregate(self, *args, **kwargs):
        return super(VerifiableManager, self).get_query_set().aggregate(*args, **kwargs)

    def annotate(self, *args, **kwargs):
        return super(VerifiableManager, self).get_query_set().annotate(*args, **kwargs)

    def complex_filter(self, *args, **kwargs):
        return super(VerifiableManager, self).get_query_set().complex_filter(*args, **kwargs)

    def exclude(self, *args, **kwargs):
        return super(VerifiableManager, self).get_query_set().exclude(*args, **kwargs)

    def in_bulk(self, *args, **kwargs):
        return super(VerifiableManager, self).get_query_set().in_bulk(*args, **kwargs)

    def iterator(self, *args, **kwargs):
        return super(VerifiableManager, self).get_query_set().iterator(*args, **kwargs)

    def latest(self, *args, **kwargs):
        return super(VerifiableManager, self).get_query_set().latest(*args, **kwargs)

    def order_by(self, *args, **kwargs):
        return super(VerifiableManager, self).get_query_set().order_by(*args, **kwargs)

    def select_for_update(self, *args, **kwargs):
        return super(VerifiableManager, self).get_query_set().select_for_update(*args, **kwargs)

    def select_related(self, *args, **kwargs):
        return super(VerifiableManager, self).get_query_set().select_related(*args, **kwargs)

    def prefetch_related(self, *args, **kwargs):
        return super(VerifiableManager, self).get_query_set().prefetch_related(*args, **kwargs)

    def values(self, *args, **kwargs):
        return super(VerifiableManager, self).get_query_set().values(*args, **kwargs)

    def values_list(self, *args, **kwargs):
        return super(VerifiableManager, self).get_query_set().values_list(*args, **kwargs)

    def update(self, *args, **kwargs):
        return super(VerifiableManager, self).get_query_set().update(*args, **kwargs)

    def reverse(self, *args, **kwargs):
        return super(VerifiableManager, self).get_query_set().reverse(*args, **kwargs)

    def defer(self, *args, **kwargs):
        return super(VerifiableManager, self).get_query_set().defer(*args, **kwargs)

    def only(self, *args, **kwargs):
        return super(VerifiableManager, self).get_query_set().only(*args, **kwargs)

    def using(self, *args, **kwargs):
        return super(VerifiableManager, self).get_query_set().using(*args, **kwargs)

    def exists(self, *args, **kwargs):
        return super(VerifiableManager, self).get_query_set().exists(*args, **kwargs)

    # Insert and update needs to then update the MACs and tree
    def _insert(self, objs, fields, **kwargs):
        return insert_query(self.model, objs, fields, **kwargs)

    def _update(self, values, **kwargs):
        return super(VerifiableManager, self)get_query_set()._update(values, **kwargs)

    # Prevent raw queries?
    def raw(self, raw_query, params=None, *args, **kwargs):
        return RawQuerySet(raw_query=raw_query, model=self.model, params=params, using=self._db, *args, **kwargs)
        

# Field methods here: https://code.djangoproject.com/browser/django/trunk/django/db/models/fields/__init__.py
# I'm just putting in a template for creating new fields.
# I'm least sure about which functions need to be overridden here....
class VerifiableCharField(models.CharField):
    
    def __init__(self, *args, **kwargs):
        # Place code here, which is excecuted the same
        # time the ``pre_init``-signal would be

        # Call parent's ``init`` function
        super(VerifiableCharField, self).__init__(*args,**kwargs)

        # Place code here, which is excecuted the same
        # time the ``post_init``-signal would be
        
    def pre_save(self, model_instance, add):
        # Place code here, which is excecuted the same
        # time the ``pre_init``-signal would be

        # Call parent's ``init`` function
        super(VerifiableCharField, self).pre_save(model_instance, add)

        # Place code here, which is excecuted the same
        # time the ``post_init``-signal would be
        

# Model methods here: https://code.djangoproject.com/browser/django/trunk/django/db/models/base.py
# Model handles the init, save, and delete operations
class VerifiableModel(models.Model):
    data_hash = models.CharField()
    # Do we want explicitly force the manager?  or change objects to verifiableObjects and let developer decide which to use?
    objects = VarifiableManager()
   
    def __init__(self, *args, **kwargs):
        # Place code here, which is excecuted the same
        # time the ``pre_init``-signal would be

        # Call parent's ``init`` function
        super(VerifiableObject, self).__init__(*args,**kwargs)

        # Place code here, which is excecuted the same
        # time the ``post_init``-signal would be
        
    def save(self, force_insert=False, force_update=False, using=None):
        # Place code here, which is excecuted the same
        # time the ``pre_save``-signal would be

        # Call parent's ``save`` function
        super(VerifiableObject, self).save(force_insert, force_update, using)

        # Place code here, which is excecuted the same
        # time the ``post_save``-signal would be
        
    def delete(self, using=None):
        # Place code here, which is excecuted the same
        # time the ``pre_delete``-signal would be

        # Call parent's ``delete`` function
        super(VerifiableObject, self).delete(using)

        # Place code here, which is excecuted the same
        # time the ``post_delete``-signal would be
