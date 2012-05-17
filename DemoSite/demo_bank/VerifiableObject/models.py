from django.db import models
from django.db.models.query import insert_query
import hashlib  # Going to be used for hashing in the hash tree
import hmac     # Going to be used for tuple macing
import sqlite3  # Store model HMAC passwords and other data
import random   # Used for generating keys

# Just want an exception we control
class VerifiableError(Exception):
    pass

class NoVerifiableIDError(Exception):
    pass

# The fields that we do not want to use when HMACing a row
def excludedField(name):
    if name == "verifiablemodel_ptr" or name == "id" or name[0] == '_':
        return True
    return False

# Does integrity check for a given row
def verifyRow(row, password):
    # Need password retrieval system
    curr_hmac = hmac.new(password)
    # Iterate over fields
    for field in sorted(row._meta.fields):
        # Don't use excluded fields
        if excludedField(field.name):
            continue
        # Update the HMAC
        curr_hmac.update(str(getattr(row, field.name)))
    # Check HMAC integrity
    if row._data_hash != curr_hmac.hexdigest():
        raise VerifiableError("Data integrity check failed")
    
# Iterates over a set of rows
def verifyQuerySet(querySet, password, verify = True, field = None, min_value = None, max_value = None, include_min = True, include_max = True):
    # First, do integrity checking of the rows
    if verify:
        for row in querySet:
            verifyRow(row, password)
        # Next, Completeness and freshness checking
        # Call can turn off completeness verification.  This is needed sometimes to prevent circular calls.
        # Call can specify a single field.  This is required when filtering on a field, as other verifiable fields will not verify correctly afterwards.
        if field is not None:
            # If using the faster implementation (that does not use freshness)
            if field._freshness == False:
                # Make sure we have the password for the field.
                if field._data_password is None:
                    field.getDataPassword()
                # Order the rows, so we can check sequentially
                querySetRows = querySet.order_by(field.name, "-id")
                if querySetRows.is_reversed:
                    querySetRows = querySetRows.reverse()
                count = querySet.count()
                # Make sure the query set has rows
                if count > 0:
                    # Check the first row
                    firstRow = querySetRows[0]
                    prevId = getattr(firstRow, "_" + field.verifiableId + "_PREV")
                    nextId = getattr(firstRow, "_" + field.verifiableId + "_NEXT")
                    # Check min value for first row
		    check_value = getattr(firstRow, field.name)
		    if type(check_value) == int and min_value is not None:
			min_value = int(min_value)
		    if min_value is not None:
                        if include_min:
                            if check_value < min_value:
                                raise VerifiableError("Data integrity check failed")
                        else:
                            if check_value <= min_value:
                                raise VerifiableError("Data integrity check failed")
                    # If there are rows before first row
                    if prevId != "None":
                        beforeRow = type(firstRow).objects.filter(id__exact=prevId, VERIFY=False)[0]
                        # Check that before row outside min
			check_value = getattr(beforeRow, field.name)
			if type(check_value) == int and min_value is not None:
				min_value = int(min_value)
                        if min_value is not None:
                            if include_min:
                                if check_value >= min_value:
                                    raise VerifiableError("Data integrity check failed")
                            else:
                                if check_value > min_value:
                                    raise VerifiableError("Data integrity check failed")
                        # Check this row really comes after the previous
                        curr_hmac = hmac.new(field._data_password)
                        curr_hmac.update(str(beforeRow.id))
                        curr_hmac.update(str(firstRow.id))
                        curr_hmac.update(str(nextId))
                        field_data_hash = getattr(firstRow, "_" + field.verifiableId + "_HASH")
                        # Verify row ordering
                        if field_data_hash != curr_hmac.hexdigest():
                            raise VerifiableError("Data integrity check failed")
                    else:
                        # Check this row really is first
                        curr_hmac = hmac.new(field._data_password)
                        curr_hmac.update("None")
                        curr_hmac.update(str(firstRow.id))
                        curr_hmac.update(str(nextId))
                        field_data_hash = getattr(firstRow, "_" + field.verifiableId + "_HASH")
                        # Verify row ordering
                        if field_data_hash != curr_hmac.hexdigest():
                            raise VerifiableError("Data integrity check failed")
                    lastId = firstRow.id
                    # Check the middle rows
                    for row in querySetRows[1:]:
                        if str(nextId) != str(row.id):
                            raise VerifiableError("Data integrity check failed")
                        nextId = getattr(row, "_" + field.verifiableId + "_NEXT")
                        # Check this row really comes after the previous
                        curr_hmac = hmac.new(field._data_password)
                        curr_hmac.update(str(lastId))
                        curr_hmac.update(str(row.id))
                        curr_hmac.update(str(nextId))
                        field_data_hash = getattr(row, "_" + field.verifiableId + "_HASH")
                        # Verify row ordering
                        if field_data_hash != curr_hmac.hexdigest():
                            raise VerifiableError("Data integrity check failed")
                        lastId = row.id
                    # Check the last row
                    lastRow = querySetRows.reverse()[0]
                    # Check max value for last row
		    check_value = getattr(firstRow, field.name)
		    if type(check_value) == int and max_value is not None:
			max_value = int(max_value)
                    if max_value is not None:
                        if include_max:
                            if check_value > max_value:
                                raise VerifiableError("Data integrity check failed")
                        else:
                            if check_value >= max_value:
                                raise VerifiableError("Data integrity check failed")
                    # Get rows after last row
                    kwargs = {
                        '%s__%s' % ("_" + field.verifiableId + "_PREV", 'exact'): lastId,
                        '%s' % ('VERIFY'): False
                    }
                    temprows = type(firstRow).objects.filter(**kwargs)
                    # If there are rows after last row
                    if temprows.count() > 0:
                        afterRow = temprows[0]
                        if str(nextId) != str(afterRow.id):
                            raise VerifiableError("Data integrity check failed")
                        nextId = getattr(afterRow, "_" + field.verifiableId + "_NEXT")
                        # Check that after row is outside max value
			check_value = getattr(afterRow, field.name)
			if type(check_value) == int and max_value is not None:
			    max_value = int(max_value)
                        if max_value is not None:
                            if include_min:
                                if check_value <= max_value:
                                    raise VerifiableError("Data integrity check failed")
                            else:
                                if check_value < max_value:
                                    raise VerifiableError("Data integrity check failed")
                        # Check this row really comes after the last row
                        curr_hmac = hmac.new(field._data_password)
                        curr_hmac.update(str(lastId))
                        curr_hmac.update(str(afterRow.id))
                        curr_hmac.update(str(nextId))
                        field_data_hash = getattr(afterRow, "_" + field.verifiableId + "_HASH")
                        # Verify row ordering
                        if field_data_hash != curr_hmac.hexdigest():
                            raise VerifiableError("Data integrity check failed")
            # Otherwise, use tree-based completeness (with freshness)
            else:
                pass
                #field._tree.verify(min_value, max_value, querySet, include_min, include_max)
        # Field was not set, so check all fields.
        else:
            # Make sure queryset has rows
            if querySet.count() > 0:
                # Get the first row, so we can check its fields
                model = querySet[0]
                # Iterate over the fields
                for field in sorted(model._meta.fields):
                    # Ignore excluded fields
                    if excludedField(field.name):
                        continue
                    # Verify completeness for field, if its a verifiable field
                    if isinstance(field, VerifiableField):
                        # If using the faster implementation (that does not use freshness)
                        if field._freshness == False:
                            # Make sure we have the password
                            if field._data_password is None:
                                field.getDataPassword()
                            # Order the rows so we can verify sequentially.
                            querySetRows = querySet.order_by(field.name, "-id")
                            if querySetRows.is_reversed:
                                querySetRows = querySetRows.reverse()
                            count = querySetRows.count()
                            # Make sure the query set has rows
                            if count > 0:
                                # Check the first row
                                firstRow = querySetRows[0]
                                prevId = getattr(firstRow, "_" + field.verifiableId + "_PREV")
                                nextId = getattr(firstRow, "_" + field.verifiableId + "_NEXT")
                                # If there are rows before first row
                                if prevId != "None":
                                    beforeRow = type(firstRow).objects.filter(id__exact=prevId, VERIFY=False)[0]
                                    # Check this row really comes after the previous
                                    curr_hmac = hmac.new(field._data_password)
                                    curr_hmac.update(str(beforeRow.id))
                                    curr_hmac.update(str(firstRow.id))
                                    curr_hmac.update(str(nextId))
                                    field_data_hash = getattr(firstRow, "_" + field.verifiableId + "_HASH")
                                    # Verify row ordering
                                    if field_data_hash != curr_hmac.hexdigest():
                                        raise VerifiableError("Data integrity check failed")
                                else:
                                    # Check this row really is first
                                    curr_hmac = hmac.new(field._data_password)
                                    curr_hmac.update("None")
                                    curr_hmac.update(str(firstRow.id))
                                    curr_hmac.update(str(nextId))
                                    field_data_hash = getattr(firstRow, "_" + field.verifiableId + "_HASH")
                                    # Verify row ordering
                                    if field_data_hash != curr_hmac.hexdigest():
                                        raise VerifiableError("Data integrity check failed")
                                lastId = firstRow.id
                                # Check the middle rows
                                for row in querySetRows[1:]:
				    if str(nextId) != str(row.id):
                                        raise VerifiableError("Data integrity check failed")
                                    nextId = getattr(row, "_" + field.verifiableId + "_NEXT")
                                    # Check this row really comes after the previous
                                    curr_hmac = hmac.new(field._data_password)
                                    curr_hmac.update(str(lastId))
                                    curr_hmac.update(str(row.id))
                                    curr_hmac.update(str(nextId))
                                    field_data_hash = getattr(row, "_" + field.verifiableId + "_HASH")
                                    # Verify row ordering
                                    if field_data_hash != curr_hmac.hexdigest():
                                        raise VerifiableError("Data integrity check failed")
                                    lastId = row.id
                                # Check the last row
                                lastRow = querySetRows.reverse()[0]
                                # Get rows after last row
                                kwargs = {
                                    '%s__%s' % ("_" + field.verifiableId + "_PREV", 'exact'): lastId,
                                    '%s' % ('VERIFY'): False
                                }
                                temprows = type(firstRow).objects.filter(**kwargs)
                                # If there are rows after last row
                                if temprows.count() > 0:
                                    afterRow = temprows[0]
                                    if str(nextId) != str(afterRow.id):
                                        raise VerifiableError("Data integrity check failed")
                                    nextId = getattr(afterRow, "_" + field.verifiableId + "_NEXT")
                                    # Check this row really comes after the last row
                                    curr_hmac = hmac.new(field._data_password)
                                    curr_hmac.update(str(lastId))
                                    curr_hmac.update(str(afterRow.id))
                                    curr_hmac.update(str(nextId))
                                    field_data_hash = getattr(afterRow, "_" + field.verifiableId + "_HASH")
                                    # Verify row ordering
                                    if field_data_hash != curr_hmac.hexdigest():
                                        raise VerifiableError("Data integrity check failed")
                        # Otherwise, use tree-based completeness (with freshness)
                        else:
                            pass
                            #field._tree.verify(min_value, max_value, querySet, include_min, include_max)

# Needed in order to verify queries (in case of sequential calls like queryset.all().filter().etc)
# Methods for QuerySet: https://code.djangoproject.com/browser/django/trunk/django/db/models/query.py
class VerifiableQuerySet(models.query.QuerySet):
    # Data password for the model contained in this query set
    _data_password = None
    # Holds whether current query set has been filtered by a verifiable field.  Can't do this twice.
    can_be_filtered = True
    # Holds whether the current query is reversed (affects order_by queries)
    is_reversed = False
    
    def __init__(self, password, can_be_filtered, is_reversed, model=None, query=None, using=None):
        self._data_password = password
        self.can_be_filtered = can_be_filtered
        self.is_reversed = is_reversed
        super(VerifiableQuerySet, self).__init__(model, query, using)
    
    # Aggregation not supported.
    def aggregate(self, *args, **kwargs):
        """
        Returns a dictionary containing the calculations (aggregation)
        over the current queryset

        If args is present the expression is passed as a kwarg using
        the Aggregate object's default alias.
        """
        raise VerifiableError("Aggregate not supported")

    # Returns the count of the current query set
    def count(self):
        """
        Performs a SELECT COUNT() and returns the number of records as an
        integer.

        If the QuerySet is already fully cached this simply returns the length
        of the cached results set to avoid multiple SELECT COUNT(*) calls.
        """
        return super(VerifiableQuerySet, self).count()

    # Gets a single row, need to validate
    def get(self, *args, **kwargs):
        """
        Performs the query and returns a single object matching the given
        keyword arguments.
        """     
        row = super(VerifiableQuerySet, self).get(*args, **kwargs)
        verifyRow(row, self._data_password)
        return row

    # This will call save(), which should handle the HMAC
    # Does, however, need to setup completeness for new row
    def create(self, **kwargs):
        """
        Creates a new object with the given kwargs, saving it to the database
        and returning the created object.
        """
        # Create the object
        obj = self.model(**kwargs)
        self._for_write = True
        # Save it to get an ID
        obj.save(force_insert=True, using=self.db)
        # Iterate over fields
        for field in sorted(obj._meta.fields):
            # Don't check excluded fields
            if excludedField(field.name):
                continue
            # Setup completeness for verifiable fields
            if isinstance(field, VerifiableField):
                # If using quicker completeness with no freshness
                if field._freshness == False:
                    # Make sure we have the data password
                    if field._data_password is None:
                        field.getDataPassword()
                    # If this is the first row being created
                    rows1 = type(obj).objects.get_query_set().exclude(id__exact=obj.id, VERIFY=False)
                    if (type(obj).objects.get_query_set().count() == 1):
                        # Set values for first row
                        setattr(obj, "_" + field.verifiableId + "_PREV", "None")
                        setattr(obj, "_" + field.verifiableId + "_NEXT", "None")
                        curr_hmac = hmac.new(field._data_password)
                        curr_hmac.update("None")
                        curr_hmac.update(str(obj.id))
                        curr_hmac.update("None")
                        setattr(obj, "_" + field.verifiableId + "_HASH", curr_hmac.hexdigest())
                        # Save
                        #obj.save(force_update=True, using=self.db)
                    # If there are already other rows
                    else:
                        # Get all the rows that will be after new row, and get the smallest
                        value = getattr(obj, field.name)
                        kwargs = { 
                            '%s__%s' % (field.name, 'gte'): value,
                            '%s' % ('VERIFY'): False
                        }
                        rows2 = rows1.filter(**kwargs).order_by(field.name, "-id")
                        # If current row will be the last row
                        if rows2.count() == 0:
                            # Get the row directly before current row
                            row = rows1.order_by(field.name, "-id").reverse()[0]
                            # Set the PREV and NEXt value
                            setattr(obj, "_" + field.verifiableId + "_PREV", row.id)
                            #obj.save(force_update=True, using=self.db)
                            setattr(obj, "_" + field.verifiableId + "_NEXT", "None")
                            #obj.save(force_update=True, using=self.db)
                            
                            # Set the HASH value
                            curr_hmac = hmac.new(field._data_password)
                            curr_hmac.update(str(getattr(obj, "_" + field.verifiableId + "_PREV")))
                            curr_hmac.update(str(obj.id))
                            curr_hmac.update("None")
                            setattr(obj, "_" + field.verifiableId + "_HASH", curr_hmac.hexdigest())
                            #obj.save(force_update=True, using=self.db)
                            
                            # Update the row before, to point to current row
                            setattr(row, "_" + field.verifiableId + "_NEXT", str(obj.id))
                            curr_hmac = hmac.new(field._data_password)
                            curr_hmac.update(str(getattr(row, "_" + field.verifiableId + "_PREV")))
			    #chazz curr_hmac.update(str(getattr(row, "_" + field.verifiableId + "_NEXT")))
                            curr_hmac.update(str(row.id))
                            curr_hmac.update(str(obj.id))
                            setattr(row, "_" + field.verifiableId + "_HASH", str(curr_hmac.hexdigest()))
                            row.save(force_update=True, using=self.db)
                            
                        # If there will be other rows after current row
                        else:
                            # Get the row directly after current row
                            row = rows2[0]
                            rowPrev = getattr(row, "_" + field.verifiableId + "_PREV")
                            # Set the PREV and NEXT value
                            setattr(obj, "_" + field.verifiableId + "_PREV", rowPrev)
                            #obj.save(force_update=True, using=self.db)
                            setattr(obj, "_" + field.verifiableId + "_NEXT", row.id)
                            #obj.save(force_update=True, using=self.db)
                            
                            # If current row to become new first row
                            if rowPrev == "None":
                                # Set the HASH value for first row
                                curr_hmac = hmac.new(field._data_password)
                                curr_hmac.update("None")
                                curr_hmac.update(str(obj.id))
                                curr_hmac.update(str(row.id))
                                setattr(obj, "_" + field.verifiableId + "_HASH", str(curr_hmac.hexdigest()))
                                #obj.save(force_update=True, using=self.db)
                            # Not first row
                            else:
                                # Set the HASH value
                                curr_hmac = hmac.new(field._data_password)
                                curr_hmac.update(str(getattr(obj, "_" + field.verifiableId + "_PREV")))
                                curr_hmac.update(str(obj.id))
                                curr_hmac.update(str(getattr(obj, "_" + field.verifiableId + "_NEXT")))
                                setattr(obj, "_" + field.verifiableId + "_HASH", str(curr_hmac.hexdigest()))
                                #obj.save(force_update=True, using=self.db)
                                
                                # Get the row directly before current row
                                row2 = type(obj).objects.get_query_set().filter(id__exact=rowPrev, VERIFY=False)[0]
                                # Update the row before, to point to current row
                                setattr(row2, "_" + field.verifiableId + "_NEXT", obj.id)
                                curr_hmac = hmac.new(field._data_password)
                                curr_hmac.update(str(getattr(row2, "_" + field.verifiableId + "_PREV")))
                                curr_hmac.update(str(row2.id))
                                curr_hmac.update(str(obj.id))
                                setattr(row2, "_" + field.verifiableId + "_HASH", str(curr_hmac.hexdigest()))
                                row2.save(force_update=True, using=self.db)

                            # Update the row after, to point to current row
                            setattr(row, "_" + field.verifiableId + "_PREV", str(obj.id))
                            curr_hmac = hmac.new(field._data_password)
                            curr_hmac.update(str(obj.id))
                            curr_hmac.update(str(row.id))
                            curr_hmac.update(str(getattr(row, "_" + field.verifiableId + "_NEXT")))
                            setattr(row, "_" + field.verifiableId + "_HASH", str(curr_hmac.hexdigest()))
                            row.save(force_update=True, using=self.db)
        obj.save()
        return obj

    # Bulk create will be too complicated to implement currently.
    def bulk_create(self, objs):
        """
        Inserts each of the instances into the database. This does *not* call
        save() on each of the instances, does not send any pre/post save
        signals, and does not set the primary key attribute if it is an
        autoincrement field.
        """
        raise VerifiableError("Bulk_create not supported")

    # This will call save() if creating.  Then returns a row
    # We can then verify the row
    def get_or_create(self, **kwargs):
        """
        Looks up an object with the given kwargs, creating one if necessary.
        Returns a tuple of (object, created), where created is a boolean
        specifying whether an object was created.
        """
        (row, created) = super(VerifiableQuerySet, self).get_or_create(**kwargs)
        verifyRow(row, self._data_password)
        return (row, created)

    # Returns a single row, validate the row
    def latest(self, field_name=None):
        """
        Returns the latest object, according to the model's 'get_latest_by'
        option or optional given field_name.
        """
        row = super(VerifiableQuerySet, self).latest(field_name)
        verifyRow(row, self._data_password)
        return row

    # Don't currently know how to validate this.
    def in_bulk(self, id_list):
        """
        Returns a dictionary mapping each of the given IDs to the object with
        that ID.
        """
        raise VerifiableError("In_bulk not supported")

    # Deletion is being handled in the VerifiableModel
    def delete(self):
        """
        Deletes the records in the current QuerySet.
        """
        super(VerifiableQuerySet, self).delete()
    delete.alters_data = True

    # We will need to re-HMAC and re-setup completeness on all these rows
    # HMACing will be done when saved.
    def update(self, **kwargs):
        """
        Updates all elements in the current QuerySet, setting all the given
        fields to the appropriate values.
        """
        # For every row in the current queryset
        for obj in self:
            # Perform the update manually
            for key in kwargs:
                setattr(obj, key, kwargs[key])
            obj.save(force_update=True, using=self.db)
            # Then, iterate over fields
            for field in sorted(obj._meta.fields):
                # Don't use excluded fields
                if excludedField(field.name):
                    continue
                # If field is a verifiable field
                if isinstance(field, VerifiableField):
                    # If using quicker completeness, with no freshness
                    if field._freshness == False:
                        if field._data_password is None:
                            field.getDataPassword()
                        # If this is the only row in the set
                        if (type(obj).objects.get_query_set().exclude(id__exact=obj.id, VERIFY=False).count() == 0):
                            # Make sure PREV and HASH set correctly
                            setattr(obj, "_" + field.verifiableId + "_PREV", "None")
                            setattr(obj, "_" + field.verifiableId + "_NEXT", "None")
                            curr_hmac = hmac.new(field._data_password)
                            curr_hmac.update("None")
                            curr_hmac.update(str(obj.id))
                            curr_hmac.update("None")
                            setattr(obj, "_" + field.verifiableId + "_HASH", curr_hmac.hexdigest())
                        # If there are other rows
                        else:
                            # Remove current row from chain
                            # Check if current row is first
                            prev = getattr(obj, "_" + field.verifiableId + "_PREV")
                            next = getattr(obj, "_" + field.verifiableId + "_NEXT")
                            # If current row is first
                            if prev == 'None':
                                # Get the next row
                                kwargs = {
                                    '%s__%s' % ("_" + field.verifiableId + "_PREV", 'exact'): obj.id,
                                    '%s' % ('VERIFY'): False
                                }
                                rows = type(obj).objects.get_query_set().filter(**kwargs)
                                # If there is another row
                                if rows.count() > 0:
                                    # Make PREV and HASH representative of first row (it is now first)
                                    row = type(obj).objects.get_query_set().filter(**kwargs)[0]
                                    setattr(row, "_" + field.verifiableId + "_PREV", "None")
                                    curr_hmac = hmac.new(field._data_password)
                                    curr_hmac.update("None")
                                    curr_hmac.update(str(row.id))
                                    curr_hmac.update(str(getattr(row, "_" + field.verifiableId + "_NEXT")))
                                    setattr(row, "_" + field.verifiableId + "_HASH", curr_hmac.hexdigest())
                                    row.save()
                            # If not first
                            else:
                                # Get the prev row
                                kwargs = {
                                    '%s__%s' % ("_" + field.verifiableId + "_NEXT", 'exact'): obj.id,
                                    '%s' % ('VERIFY'): False
                                }
                                rows = type(obj).objects.get_query_set().filter(**kwargs)
                                # If there is a row before
                                if rows.count() > 0:
                                    row = type(obj).objects.get_query_set().filter(**kwargs)[0]
                                    # Set PREV to current rows PREV
                                    setattr(row, "_" + field.verifiableId + "_NEXT", str(getattr(obj, "_" + field.verifiableId + "_NEXT")))
                                    row.save()
                                    # Set HASH of next row using new PREV value
                                    curr_hmac = hmac.new(field._data_password)
                                    curr_hmac.update(str(getattr(row, "_" + field.verifiableId + "_PREV")))
                                    curr_hmac.update(str(row.id))
                                    curr_hmac.update(str(getattr(row, "_" + field.verifiableId + "_NEXT")))
                                    setattr(row, "_" + field.verifiableId + "_HASH", str(curr_hmac.hexdigest()))
                                    row.save()
                                
                                # Get the next row
                                kwargs = {
                                    '%s__%s' % ("_" + field.verifiableId + "_PREV", 'exact'): obj.id,
                                    '%s' % ('VERIFY'): False
                                }
                                rows = type(obj).objects.get_query_set().filter(**kwargs)
                                # If there is a row after
                                if rows.count() > 0:
                                    row = type(obj).objects.get_query_set().filter(**kwargs)[0]
                                    # Set PREV to current rows PREV
                                    setattr(row, "_" + field.verifiableId + "_PREV", str(getattr(obj, "_" + field.verifiableId + "_PREV")))
                                    # Set HASH of next row using new PREV value
                                    curr_hmac = hmac.new(field._data_password)
                                    curr_hmac.update(str(getattr(row, "_" + field.verifiableId + "_PREV")))
                                    curr_hmac.update(str(row.id))
                                    curr_hmac.update(str(getattr(row, "_" + field.verifiableId + "_NEXT")))
                                    setattr(row, "_" + field.verifiableId + "_HASH", str(curr_hmac.hexdigest()))
                                    row.save()
                                        
                            # Add row back into chain
                            # Find the value for the field in current row
                            value = getattr(obj, field.name)
                            # Find all rows that come after current row
                            kwargs = {
                                '%s__%s' % (field.name, 'gte'): value,
                                '%s' % ('VERIFY'): False
                            }
                            rows = type(obj).objects.get_query_set().filter(**kwargs).exclude(id__exact=obj.id, VERIFY=False).order_by(field.name, "-id")
                            # If current row is going to be the last row
                            if rows.count() == 0:
                                # Get the row previous to current one
                                row = type(obj).objects.get_query_set().exclude(id__exact=obj.id, VERIFY=False).order_by(field.name, "-id").reverse()[0]
                                # Set the PREV and NEXT value
                                setattr(obj, "_" + field.verifiableId + "_PREV", row.id)
                                #obj.save(force_update=True, using=self.db)
                                setattr(obj, "_" + field.verifiableId + "_NEXT", "None")
                                #obj.save(force_update=True, using=self.db)
                                
                                # Set the HASH value
                                curr_hmac = hmac.new(field._data_password)
                                curr_hmac.update(str(getattr(obj, "_" + field.verifiableId + "_PREV")))
                                curr_hmac.update(str(obj.id))
                                curr_hmac.update("None")
                                setattr(obj, "_" + field.verifiableId + "_HASH", curr_hmac.hexdigest())
                                #obj.save(force_update=True, using=self.db)
                                
                                # Update the row before, to point to current row
                                setattr(row, "_" + field.verifiableId + "_NEXT", str(obj.id))
                                curr_hmac = hmac.new(field._data_password)
                                curr_hmac.update(str(getattr(row, "_" + field.verifiableId + "_PREV")))
                                curr_hmac.update(str(row.id))
                                curr_hmac.update(str(obj.id))
                                setattr(row, "_" + field.verifiableId + "_HASH", str(curr_hmac.hexdigest()))
                                row.save(force_update=True, using=self.db)
                                
                            # If current row has rows after current row
                            else:
                                # Get the row after the current one
                                row = type(obj).objects.get_query_set().filter(**kwargs).exclude(id__exact=obj.id, VERIFY=False).order_by(field.name, "-id")[0]
                                rowPrev = getattr(row, "_" + field.verifiableId + "_PREV")
                                # Set the PREV and NEXT value
                                setattr(obj, "_" + field.verifiableId + "_PREV", rowPrev)
                                #obj.save(force_update=True, using=self.db)
                                setattr(obj, "_" + field.verifiableId + "_NEXT", row.id)
                                #obj.save(force_update=True, using=self.db)
                                
                                # If current row to become new first row
                                if rowPrev == "None":
                                    # Set the HASH value for first row
                                    curr_hmac = hmac.new(field._data_password)
                                    curr_hmac.update("None")
                                    curr_hmac.update(str(obj.id))
                                    curr_hmac.update(str(row.id))
                                    setattr(obj, "_" + field.verifiableId + "_HASH", str(curr_hmac.hexdigest()))
                                    #obj.save(force_update=True, using=self.db)
                                # Not first row
                                else:
                                    # Set the HASH value for regular row
                                    curr_hmac = hmac.new(field._data_password)
                                    curr_hmac.update(str(getattr(obj, "_" + field.verifiableId + "_PREV")))
                                    curr_hmac.update(str(obj.id))
                                    curr_hmac.update(str(getattr(obj, "_" + field.verifiableId + "_NEXT")))
                                    setattr(obj, "_" + field.verifiableId + "_HASH", str(curr_hmac.hexdigest()))
                                    #obj.save(force_update=True, using=self.db)
                                    
                                    # Get the row directly before current row
                                    row2 = type(obj).objects.get_query_set().exclude(id__exact=obj.id, VERIFY=False).order_by(field.name, "-id").reverse()[0]
                                    # Update the row before, to point to current row
                                    setattr(row2, "_" + field.verifiableId + "_NEXT", obj.id)
                                    curr_hmac = hmac.new(field._data_password)
                                    curr_hmac.update(str(getattr(row2, "_" + field.verifiableId + "_PREV")))
                                    curr_hmac.update(str(row2.id))
                                    curr_hmac.update(str(obj.id))
                                    setattr(row2, "_" + field.verifiableId + "_HASH", str(curr_hmac.hexdigest()))
                                    row2.save(force_update=True, using=self.db)

                                # Update the next row to point to current row
                                setattr(row, "_" + field.verifiableId + "_PREV", str(obj.id))
                                curr_hmac = hmac.new(field._data_password)
                                curr_hmac.update(str(obj.id))
                                curr_hmac.update(str(row.id))
                                curr_hmac.update(str(getattr(row, "_" + field.verifiableId + "_NEXT")))
                                setattr(row, "_" + field.verifiableId + "_HASH", str(curr_hmac.hexdigest()))
                                row.save(force_update=True, using=self.db)
            # Make sure we saved
            obj.save(force_update=True, using=self.db)
    update.alters_data = True

    # TODO: figure out if this needs to update the HMACs
    #def _update(self, values):
    #    """
    #    A version of update that accepts field objects instead of field names.
    #    Used primarily for model saving and not intended for use by general
    #    code (it requires too much poking around at model internals to be
    #    useful at that level).
    #    """
    #    print type(values)
    #    for row in self:
    #        for name, types, val in values:
    #            setattr(row, name.name, val)
    #        #row.save()
    #    return self.count()
    #_update.alters_data = True

    # Shouldn't need to override.
    def exists(self):
        return super(VerifiableQuerySet, self).exists()

    ##################################################
    # PUBLIC METHODS THAT RETURN A QUERYSET SUBCLASS #
    ##################################################

    # Verifiable Values Query Set has been implemented.
    def values(self, *fields):
        return self._clone(klass=VerifiableValuesQuerySet, setup=True, _fields=fields)

    # Verifiable Values List Query Set has been implemented.
    def values_list(self, *fields, **kwargs):
        flat = kwargs.pop('flat', False)
        if kwargs:
            raise TypeError('Unexpected keyword arguments to values_list: %s'
                % (kwargs.keys(),))
        if flat and len(fields) > 1:
            raise TypeError("'flat' is not valid when values_list is called with more than one field.")
        return self._clone(klass=VerifiableValuesListQuerySet, setup=True, flat=flat, _fields=fields)

    # Verifiable Date Query Set has been implemented.
    def dates(self, field_name, kind, order='ASC'):
        """
        Returns a list of datetime objects representing all available dates for
        the given field_name, scoped to 'kind'.
        """

        assert kind in ("month", "year", "day"), \
                        "'kind' must be one of 'year', 'month' or 'day'."
                        
        assert order in ('ASC', 'DESC'), \
                        "'order' must be either 'ASC' or 'DESC'."
        return self._clone(klass=VerifiableDateQuerySet, setup=True, _field_name=field_name, _kind=kind, _order=order)

    # VerifiableEmptyQuerySet is implemented
    def none(self):
        """
        Returns an empty VerifiableQuerySet.
        """
        return self._clone(klass=VerifiableEmptyQuerySet)

    ##################################################################
    # PUBLIC METHODS THAT ALTER ATTRIBUTES AND RETURN A NEW QUERYSET #
    ##################################################################

    # Returns all rows
    def all(self):
        """
        Returns a new QuerySet that is a copy of the current one. This allows a
        QuerySet to proxy for a model manager in some cases.
        """
        querySet = super(VerifiableQuerySet, self).all()
        if querySet.can_be_filtered:
            verifyQuerySet(querySet, self._data_password)
        return querySet

    # Filters the rows, need to check filter, then verify afterwards
    def filter(self, *args, **kwargs):
        """
        Returns a new QuerySet instance with the args ANDed to the existing
        set.
        """
        includeMin = False
        includeMax = False
        minval = None
        maxval = None
        vfield = None
        vcount = 0
        verify = kwargs.get('VERIFY', True)
        can_be_filtered = True
        if verify:
            for key in kwargs:
                parts = key.split('__')
                field = None
                for f in self.model._meta.fields:
                    if f.name == parts[0]:
                        field = f
                        break
                if not field:
                    break
                if isinstance(field, VerifiableField):
                    if not self.can_be_filtered or vcount > 1:
                        raise VerifiableError("Cannot filter on two verifiable fields")
                    can_be_filtered = False
                    vfield = field
                    if len(parts) == 1:
                        minval = kwargs[key]
                        maxval = kwargs[key]
                        includeMin = True
                        includeMax = True
                    elif parts[1] == 'gt':
                        includeMin = False
                        minval = kwargs[key]
                        maxval = None
                        vcount += 1
                    elif parts[1] == 'lt':
                        includeMax = False
                        maxval = kwargs[key]
                        minval = None
                        vcount += 1
                    elif parts[1] == 'gte':
                        includeMin = True
                        minval = kwargs[key]
                        maxval = None
                        vcount += 1
                    elif parts[1] == 'lte':
                        includeMax = True
                        maxval = kwargs[key]
                        minval = None
                        vcount += 1
                    elif parts[1] == 'range':
                        includeMax = True
                        includeMin = True
                        (minval, maxval) = kwargs[key]
                        vcount += 1
                    else:
                        raise VerifiableError("Cannot support " + parts[1] + " operator on filters")
        if kwargs.has_key('VERIFY'):
            del kwargs['VERIFY']
        querySet = super(VerifiableQuerySet, self).filter(*args, **kwargs)
        if vfield is not None:
            verifyQuerySet(querySet, self._data_password, verify, vfield, minval, maxval, includeMin, includeMax)
        querySet.can_be_filtered = can_be_filtered
        return querySet

    # Excludes the rows, need to check excludes, then verify afterwards
    def exclude(self, *args, **kwargs):
        """
        Returns a new QuerySet instance with NOT (args) ANDed to the existing
        set.
        """
        includeMin = False
        includeMax = False
        minval = None
        maxval = None
        vfield = None
        vcount = 0
        verify = kwargs.get('VERIFY', True)
        can_be_filtered = True
        if verify:
            for key in kwargs:
                parts = key.split('__')
                field = None
                for f in self.model._meta.fields:
                    if f.name == parts[0]:
                        field = f
                        break
                if not field:
                    break
                if isinstance(field, VerifiableField):
                    vcount += 1
                    if not self.can_be_filtered or vcount > 1:
                        raise VerifiableError("Cannot filter on two verifiable fields")
                    can_be_filtered = False
                    vfield = field
                    if parts[1] == 'gt':
                        includeMin = True
                        minval = kwarfs[key]
                    elif parts[1] == 'lt':
                        includeMax = True
                        maxval = kwargs[key]
                    elif parts[1] == 'gte':
                        uncludeMin = False
                        minval = kwargs[key]
                    elif parts[1] == 'lte':
                        includeMax = False
                        maxval = kwargs[key]
                    else:
                        raise VerifiableError("Cannot support " + parts[1] + " operator on filters")
                    
        if kwargs.has_key('VERIFY'):
            del kwargs['VERIFY']
        querySet = super(VerifiableQuerySet, self).exclude(*args, **kwargs)
        verifyQuerySet(querySet, self._data_password, verify, vfield, minval, maxval, includeMin, includeMax)
        querySet.can_be_filtered = can_be_filtered
        return querySet

    # Not going to handle complex filters.  Just chain filters using filter.
    def complex_filter(self, filter_obj):
        """
        Returns a new QuerySet instance with filter_obj added to the filters.

        filter_obj can be a Q object (or anything with an add_to_query()
        method) or a dictionary of keyword lookup arguments.

        This exists to support framework features such as 'limit_choices_to',
        and usually it will be more natural to use other methods.
        """
        raise VerifiableError("Complex_filter not supported")

    # Locks the table.  Shouldn't affect validation
    def select_for_update(self, **kwargs):
        """
        Returns a new QuerySet instance that will select objects with a
        FOR UPDATE lock.
        """
        return super(VerifiableQuerySet, self).select_for_update(**kwargs)

    # Caches related tables.  Shouldn't affect validation
    def select_related(self, *fields, **kwargs):
        """
        Returns a new QuerySet instance that will select related objects.

        If fields are specified, they must be ForeignKey fields and only those
        related objects are included in the selection.
        """
        return super(VerifiableQuerySet, self).select_related(*fields, **kwargs)

    # Prefetches related tables.  Shouldn't affect validation
    def prefetch_related(self, *lookups):
        """
        Returns a new QuerySet instance that will prefetch the specified
        Many-To-One and Many-To-Many related objects when the QuerySet is
        evaluated.

        When prefetch_related() is called more than once, the list of lookups to
        prefetch is appended to. If prefetch_related(None) is called, the
        the list is cleared.
        """
        return super(VerifiableQuerySet, self).prefetch_related(*lookups)

    # Retrieves the relations.  Shouldn't affect validation
    def dup_select_related(self, other):
        """
        Copies the related selection status from the QuerySet 'other' to the
        current QuerySet.
        """
        super(VerifiableQuerySet, self).dup_select_related(other)

    # Annotation adds columns.  Will break integrity checking.
    def annotate(self, *args, **kwargs):
        """
        Return a query set in which the returned objects have been annotated
        with data aggregated from related fields.
        """
        raise VerifiableError("Annotate not supported")

    # Reorders the columns.  Shouldn't affect validation.
    def order_by(self, *field_names):
        """
        Returns a new QuerySet instance with the ordering changed.
        """
        return super(VerifiableQuerySet, self).order_by(*field_names)

    # Need to verify after distinct. TODO: Will this break completeness?
    def distinct(self, *field_names):
        """
        Returns a new QuerySet instance that will select only distinct results.
        """
        #raise VerifiableError("Annotate not supported")
        querySet = super(VerifiableQuerySet, self).distinct(*field_names)
        verifyQuerySet(querySet, self._data_password)
        return querySet

    # Do not want to handle raw sql.  Prevented.
    def extra(self, select=None, where=None, params=None, tables=None,
              order_by=None, select_params=None):
        """
        Adds extra SQL fragments to the query.
        """
        raise VerifiableError("Extra not supported")

    # Reverses the rows.  Shouldn't affect validation
    def reverse(self):
        """
        Reverses the ordering of the QuerySet.
        """
        self.is_reversed = not self.is_reversed
        return super(VerifiableQuerySet, self).reverse()

    # Prevents fields from being loaded until requested.  Prevented (need all fields for verification)
    def defer(self, *fields):
        """
        Defers the loading of data for certain fields until they are accessed.
        The set of fields to defer is added to any existing set of deferred
        fields. The only exception to this is if None is passed in as the only
        parameter, in which case all deferrals are removed (None acts as a
        reset option).
        """
        raise VerifiableError("Defer not supported")

    # Only allows fields to be loaded until requested.  Prevented (need all fields for verification)
    def only(self, *fields):
        """
        Essentially, the opposite of defer. Only the fields passed into this
        method and that are not already specified as deferred are loaded
        immediately when the queryset is evaluated.
        """
        raise VerifiableError("Only not supported")

    # Probably don't want to support multiple database, but this function is used in Django's internals.
    def using(self, alias):
        """
        Selects which database this QuerySet should excecute its query against.
        """
        return super(VerifiableQuerySet, self).using(alias)

    ###################################
    # PUBLIC INTROSPECTION ATTRIBUTES #
    ###################################

    # Checks if results ordered.  Shouldn't affect verification
    def ordered(self):
        """
        Returns True if the QuerySet is ordered -- i.e. has an order_by()
        clause or a default ordering on the model.
        """
        return super(VerifiableQuerySet, self).ordered()
    ordered = property(ordered)
    
    # I think I need to override this so that it passes the data_password into the init
    def _clone(self, klass=None, setup=False, **kwargs):
        if klass is None:
            klass = self.__class__
        query = self.query.clone()
        if self._sticky_filter:
            query.filter_is_sticky = True
        c = klass(self._data_password, self.can_be_filtered, self.is_reversed, model=self.model, query=query, using=self._db)
        c._for_write = self._for_write
        c.__dict__.update(kwargs)
        if setup and hasattr(c, '_setup_query'):
            c._setup_query()
        return c

# Basically a copy of the EmptyQuerySet, but needed it to inherit Verifiable.
class VerifiableEmptyQuerySet(VerifiableQuerySet):
    def __init__(self, password, can_be_filtered, is_reversed, model=None, query=None, using=None):
        super(VerifiableEmptyQuerySet, self).__init__(password, can_be_filtered, is_reversed, model, query, using)
        self._result_cache = []

    def __and__(self, other):
        return self._clone()

    def __or__(self, other):
        return other._clone()

    def count(self):
        return 0

    def delete(self):
        pass

    def _clone(self, klass=None, setup=False, **kwargs):
        c = super(VerifiableEmptyQuerySet, self)._clone(klass, setup=setup, **kwargs)
        c._result_cache = []
        return c

    def iterator(self):
        # This slightly odd construction is because we need an empty generator
        # (it raises StopIteration immediately).
        yield iter([]).next()

    def all(self):
        """
        Always returns EmptyQuerySet.
        """
        return self

    def filter(self, *args, **kwargs):
        """
        Always returns EmptyQuerySet.
        """
        return self

    def exclude(self, *args, **kwargs):
        """
        Always returns EmptyQuerySet.
        """
        return self

    # Prevented, because prevented above
    def complex_filter(self, filter_obj):
        """
        Always returns EmptyQuerySet.
        """
        raise VerifiableError("Complex_filter not supported")
        #return self

    def select_related(self, *fields, **kwargs):
        """
        Always returns EmptyQuerySet.
        """
        return self

    # Prevented, because prevented above
    def annotate(self, *args, **kwargs):
        """
        Always returns EmptyQuerySet.
        """
        raise VerifiableError("Annotate not supported")
        #return self

    def order_by(self, *field_names):
        """
        Always returns EmptyQuerySet.
        """
        return self

    def distinct(self, fields=None):
        """
        Always returns EmptyQuerySet.
        """
        return self

    # Prevented, because prevented above
    def extra(self, select=None, where=None, params=None, tables=None,
              order_by=None, select_params=None):
        """
        Always returns EmptyQuerySet.
        """
        raise VerifiableError("Extra not supported")
        #assert self.query.can_filter(), \
        #        "Cannot change a query once a slice has been taken"
        #return self

    def reverse(self):
        """
        Always returns EmptyQuerySet.
        """
        return self

    # Prevented, because prevented above
    def defer(self, *fields):
        """
        Always returns EmptyQuerySet.
        """
        return self

    # Prevented, because prevented above
    def only(self, *fields):
        """
        Always returns EmptyQuerySet.
        """
        return self

    def update(self, **kwargs):
        """
        Don't update anything.
        """
        return 0

    # Prevented, because prevented above
    def aggregate(self, *args, **kwargs):
        """
        Return a dict mapping the aggregate names to None
        """
        raise VerifiableError("Aggregate not supported")
        #for arg in args:
        #    kwargs[arg.default_alias] = arg
        #return dict([(key, None) for key in kwargs])

    # EmptyQuerySet is always an empty result in where-clauses (and similar
    # situations).
    value_annotation = False

# Specialized query set for values
class VerifiableValuesQuerySet(VerifiableQuerySet):
    def __init__(self, password, *args, **kwargs):
        super(VerifiableValuesQuerySet, self).__init__(password, *args, **kwargs)
        # select_related isn't supported in values(). (FIXME -#3358)
        self.query.select_related = False

        # QuerySet.clone() will also set up the _fields attribute with the
        # names of the model fields to select.

    def iterator(self):
        # Purge any extra columns that haven't been explicitly asked for
        extra_names = self.query.extra_select.keys()
        field_names = self.field_names
        aggregate_names = self.query.aggregate_select.keys()

        names = extra_names + field_names + aggregate_names

        for row in self.query.get_compiler(self.db).results_iter():
            verifyRow(row, self._data_password)
            result = dict(zip(names, row))
            #HIDES EXTRA FIELD
            #if hasattr(result, mac_field_name): del result[mac_field_name]
            yield result

    def _setup_query(self):
        """
        Constructs the field_names list that the values query will be
        retrieving.

        Called by the _clone() method after initializing the rest of the
        instance.
        """
        self.query.clear_deferred_loading()
        self.query.clear_select_fields()

        if self._fields:
            self.extra_names = []
            self.aggregate_names = []
            if not self.query.extra and not self.query.aggregates:
                # Short cut - if there are no extra or aggregates, then
                # the values() clause must be just field names.
                self.field_names = list(self._fields)
            else:
                self.query.default_cols = False
                self.field_names = []
                for f in self._fields:
                    # we inspect the full extra_select list since we might
                    # be adding back an extra select item that we hadn't
                    # had selected previously.
                    if f in self.query.extra:
                        self.extra_names.append(f)
                    elif f in self.query.aggregate_select:
                        self.aggregate_names.append(f)
                    else:
                        self.field_names.append(f)
        else:
            # Default to all fields.
            self.extra_names = None
            self.field_names = [f.attname for f in self.model._meta.fields]
            self.aggregate_names = None

        self.query.select = []
        if self.extra_names is not None:
            self.query.set_extra_mask(self.extra_names)
        self.query.add_fields(self.field_names, True)
        if self.aggregate_names is not None:
            self.query.set_aggregate_mask(self.aggregate_names)

    def _clone(self, klass=None, setup=False, **kwargs):
        """
        Cloning a ValuesQuerySet preserves the current fields.
        """
        c = super(ValuesQuerySet)._clone(klass, **kwargs)
        if not hasattr(c, '_fields'):
            # Only clone self._fields if _fields wasn't passed into the cloning
            # call directly.
            c._fields = self._fields[:]
        c.field_names = self.field_names
        c.extra_names = self.extra_names
        c.aggregate_names = self.aggregate_names
        if setup and hasattr(c, '_setup_query'):
            c._setup_query()
        return c

    def _merge_sanity_check(self, other):
        super(VerifiableValuesQuerySet, self)._merge_sanity_check(other)
        if (set(self.extra_names) != set(other.extra_names) or
            set(self.field_names) != set(other.field_names) or
            self.aggregate_names != other.aggregate_names):
            raise TypeError("Merging '%s' classes must involve the same values in each case."
                % self.__class__.__name__)

    def _setup_aggregate_query(self, aggregates):
        """
        Prepare the query for computing a result that contains aggregate annotations.
        """
        self.query.set_group_by()

        if self.aggregate_names is not None:
            self.aggregate_names.extend(aggregates)
            self.query.set_aggregate_mask(self.aggregate_names)

        super(VerifiableValuesQuerySet, self)._setup_aggregate_query(aggregates)

    def _as_sql(self, connection):
        """
        For ValueQuerySet (and subclasses like ValuesListQuerySet), they can
        only be used as nested queries if they're already set up to select only
        a single field (in which case, that is the field column that is
        returned). This differs from QuerySet.as_sql(), where the column to
        select is set up by Django.
        """
        if ((self._fields and len(self._fields) > 1) or
            (not self._fields and len(self.model._meta.fields) > 1)):
            raise TypeError('Cannot use a multi-field %s as a filter value.'
                    % self.__class__.__name__)

        obj = self._clone()
        if obj._db is None or connection == connections[obj._db]:
            return obj.query.get_compiler(connection=connection).as_nested_sql()
        raise ValueError("Can't do subqueries with queries on different DBs.")

    def _prepare(self):
        """
        Validates that we aren't trying to do a query like
        value__in=qs.values('value1', 'value2'), which isn't valid.
        """
        if ((self._fields and len(self._fields) > 1) or
                (not self._fields and len(self.model._meta.fields) > 1)):
            raise TypeError('Cannot use a multi-field %s as a filter value.'
                    % self.__class__.__name__)
        return self

# Specialized query set for list of values
class VerifiableValuesListQuerySet(VerifiableValuesQuerySet):
    def iterator(self):
        if self.flat and len(self._fields) ==1:
            for row in self.query.get_compiler(self.db).results_iter():
                yield row[0]
                
        elif not self.query.extra_select and not self.query.aggregate_select:
            for row in self.query.get_compiler(self.db).results_iter():
                verifyRow(row, self._data_password)
                #HIDES EXTRA FIELD
                #if hasattr(row, mac_field_name):
                #   del row[mac_field_name]

                yield tuple(row)
        else:
            # When extra(select=...) or an annotation is involved, the extra
            # cols are always at the start of the row, and we need to reorder
            # the fields to match the order in self._fields.
            extra_names = self.query.extra_select.keys()
            field_names = self.field_names
            aggregate_names = self.query.aggregate_select.keys()

            names = extra_names + field_names + aggregate_names

            # If a field list has been specified, use it. Otherwise, use the
            # full list of fields, including extras and aggregates.
            if self._fields:
                fields = list(self._fields) + filter(lambda f: f not in self._fields, aggregate_names)
            else:
                fields = names

            #HIDES EXTRA FIELD
            #if mac_field_name in fields:
                    #fields.remove(mac_field_name)

            for row in self.query.get_compiler(self.db).results_iter():
                verifyRow(row, self._data_password)
                data = dict(zip(names, row))
                yield tuple([data[f] for f in fields])

    def clone(self, *args, **kwargs):
        clone = super(VerifiableValuesListQuerySet, self)._clone(*args, **kwargs)
        if not hasattr(clone, "flat"):
            # Only assign flat if the clone didn't already get it from kwargs
            clone.flat = self.flat
        return clone

# Specialized query set for dates
class VerifiableDateQuerySet(VerifiableQuerySet):
    def iterator(self):
        return self.query.get_compiler(self.db).results_iter()

    def _setup_query(self):
        """
        Sets up any special features of the query attribute.

        Called by the _clone() method after initializing the rest of the
        instance.
        """
        self.query.clear_deferred_loading()
        self.query = self.query.clone(klass=sql.DateQuery, setup=True)
        self.query.select = []
        self.query.add_date_select(self._field_name, self._kind, self._order)

    def _clone(self, klass=None, setup=False, **kwargs):
        c = super(VerifiableDateQuerySet, self)._clone(klass, False, **kwargs)
        c._field_name = self._field_name
        c._kind = self._kind
        if setup and hasattr(c, '_setup_query'):
            c._setup_query()
        return c    

# Manager methods here: https://code.djangoproject.com/browser/django/trunk/django/db/models/manager.py
# Manager handles the queries.  Often reached by calling Model.objects.  So, overriding objects with this manager in VerifiableModel.
class VerifiableManager(models.Manager):
    use_for_related_fields = True
    _data_password = None
    
    def __init__(self):
        super(VerifiableManager, self).__init__()
    
    # Gets the password for this manager
    def getDataPassword(self, class_name):
        # Retrieve the models HMAC password
        # Creates database if doesn't exist
        conn = sqlite3.connect('verifiable.sqlite')
        c = conn.cursor()
        # Make sure table exists
        c.execute("create table if not exists model_passwords(model_name text primary key, password text)")
        # Get the list of models passwords
        c.execute("select * from model_passwords where model_name = ?", (class_name,))
        data = c.fetchone()
        # Password not set
        if data == None:
            # Create one and insert it
            self._data_password = str(random.getrandbits(256))
            c.execute("insert into model_passwords values(?,?)", (class_name, self._data_password,))
            conn.commit()
        # Password is set
        else:
            # Store it
            self._data_password = data[1]
        c.close()
        conn.close()
    
    # Returns query sets
    def get_empty_query_set(self):
        self.getDataPassword(self.model.verifiableId)
        return VerifiableEmptyQuerySet(self._data_password, True, False, self.model, using=self._db)
    
    # Returns all of the given model
    def get_query_set(self):
        self.getDataPassword(self.model.verifiableId)
        return VerifiableQuerySet(self._data_password, True, False, self.model, using=self._db)
    
    # Methods that return query sets: https://docs.djangoproject.com/en/dev/ref/models/querysets/#methods-that-return-new-querysets
    # Methods that do not return query sets: https://docs.djangoproject.com/en/dev/ref/models/querysets/#methods-that-do-not-return-querysets
    
    # Always returns empty.  Supportable
    def none(self):
        return self.get_empty_query_set()
        
    # Basic select * query.
    def all(self):
        self.getDataPassword(self.model.verifiableId)
        querySet = self.get_query_set()
        verifyQuerySet(querySet, self._data_password, None, None)
        return querySet
        
    # Rest of methods checked through VerifiableQuerySet
    
    # Insert and update needs to then update the MACs and tree  TODO: Figure this one out
    def _insert(self, values, **kwargs):
        return insert_query(self.model, values, **kwargs)

    # Prevent raw queries
    def raw(self, raw_query, params=None, *args, **kwargs):
        raise VerifiableError("Raw not supported")

# Keeping these here in case needed later
#if (self._freshness == False):
#    new_field_name = "_" + self.verifiableId + "_HASH"
#    field = models.CharField(max_length=1024)
#    field.contribute_to_class(self.model, new_field_name)
#    new_field_name = "_" + self.verifiableId + "_PREV"
#    field = models.CharField(max_length=1024)
#    field.contribute_to_class(self.model, new_field_name)

# Just need a way to identify a field as verifiable
class VerifiableField(models.Field):
    verifiableId = None
    
    # The password for this field
    _data_password = None
    # Whether to use freshness or not (faster without)
    _freshness = True
    # Holds the tree used in completeness with freshness
    _tree = None
    
    # Get the password for this field
    def getDataPassword(self):
        # Retrieve the fields HMAC password
        # Creates database if doesn't exist
        conn = sqlite3.connect('verifiable.sqlite')
        c = conn.cursor()
        # Make sure table exists
        c.execute("create table if not exists field_passwords(field_name text primary key, password text)")
        # Get the list of fields passwords
        c.execute("select * from field_passwords where field_name = ?", (self.verifiableId,))
        data = c.fetchone()
        # Password not set
        if data == None:
            # Create one and insert it
            self._data_password = str(random.getrandbits(256))
            c.execute("insert into field_passwords values(?,?)", (self.verifiableId, self._data_password,))
            conn.commit()
        # Password is set
        else:
            # Store it
            self._data_password = data[1]
        c.close()
        conn.close()
        
    def getFreshnessValue(self):
        # Retrieve the fields current freshness value
        # Creates database if doesn't exist
        conn = sqlite3.connect('verifiable.sqlite')
        c = conn.cursor()
        # Make sure table exists
        c.execute("create table if not exists field_freshness(field_name text primary key, freshness int)")
        # Get the list of fields freshness
        c.execute("select * from field_freshness where field_name = ?", (self.verifiableId,))
        data = c.fetchone()
        # Freshness not set
        if data == None:
            # Create one and insert it
            freshness_value = 0
            c.execute("insert into field_passwords values(?,?)", (self.verifiableId, freshness_value,))
            conn.commit()
        # Freshness is set
        else:
            # Get it
            freshness_value = data[1]
        c.close()
        conn.close()
        return freshness_value
        
    def incrementFreshnessValue(self):
        # Increment the fields current freshness value
        # Creates database if doesn't exist
        conn = sqlite3.connect('verifiable.sqlite')
        c = conn.cursor()
        # Make sure table exists
        c.execute("create table if not exists field_freshness(field_name text primary key, freshness integer)")
        # Get the list of fields freshness
        c.execute("select * from field_freshness where field_name = ?", (self.verifiableId,))
        data = c.fetchone()
        # Freshness not set
        if data == None:
            # Create one and insert it
            freshness_value = 0
            c.execute("insert into field_passwords values(?,?)", (self.verifiableId, freshness_value,))
            conn.commit()
        # Freshness is set
        else:
            # Get it, increment, and store
            freshness_value = data[1]
            freshness_value += 1
            c.execute("update field_passwords set freshness = ? where field_name = ?", (freshness_value, self.verifiableId,))
        c.close()
        conn.close()
        return freshness_value

# Field methods here: https://code.djangoproject.com/browser/django/trunk/django/db/models/fields/__init__.py
class VerifiableCharField(models.CharField, VerifiableField):
    # Description of this field
    description = "A verifiable char field"

    def __init__(self, verifiableId, freshness=True, *args, **kwargs):
        # Place code here, which is excecuted the same
        # time the ``pre_init``-signal would be

        #self._tree = VerifiableTree(verifiableId)
        self.verifiableId = verifiableId
        self._freshness = freshness
        self.getDataPassword()
        
        # Call parent's ``init`` function
        super(VerifiableCharField, self).__init__(*args,**kwargs)

        # Place code here, which is excecuted the same
        # time the ``post_init``-signal would be
        
# Field methods here: https://code.djangoproject.com/browser/django/trunk/django/db/models/fields/__init__.py
class VerifiableBooleanField(models.BooleanField, VerifiableField):
    # Description of this field
    description = "A verifiable boolean field"
    
    def __init__(self, verifiableId, freshness=True, *args, **kwargs):
        # Place code here, which is excecuted the same
        # time the ``pre_init``-signal would be

        #self._tree = VerifiableTree(verifiableId)
        self.verifiableId = verifiableId
        self._freshness = freshness
        self.getDataPassword()
        
        # Call parent's ``init`` function
        super(VerifiableBooleanField, self).__init__(*args,**kwargs)

        # Place code here, which is excecuted the same
        # time the ``post_init``-signal would be

# Field methods here: https://code.djangoproject.com/browser/django/trunk/django/db/models/fields/__init__.py
class VerifiableDateField(models.DateField, VerifiableField):
    # Description of this field
    description = "A verifiable date field"
    
    def __init__(self, verifiableId, freshness=True, *args, **kwargs):
        # Place code here, which is excecuted the same
        # time the ``pre_init``-signal would be

        #self._tree = VerifiableTree(verifiableId)
        self.verifiableId = verifiableId
        self._freshness = freshness
        self.getDataPassword()
        
        # Call parent's ``init`` function
        super(VerifiableDateField, self).__init__(*args,**kwargs)

        # Place code here, which is excecuted the same
        # time the ``post_init``-signal would be

# Field methods here: https://code.djangoproject.com/browser/django/trunk/django/db/models/fields/__init__.py
class VerifiableDateTimeField(models.DateTimeField, VerifiableField):
    # Description of this field
    description = "A verifiable date time field"
    
    def __init__(self, verifiableId, freshness=True, *args, **kwargs):
        # Place code here, which is excecuted the same
        # time the ``pre_init``-signal would be

        #self._tree = VerifiableTree(verifiableId)
        self.verifiableId = verifiableId
        self._freshness = freshness
        self.getDataPassword()
        
        # Call parent's ``init`` function
        super(VerifiableDateTimeField, self).__init__(*args,**kwargs)

        # Place code here, which is excecuted the same
        # time the ``post_init``-signal would be
        
# Field methods here: https://code.djangoproject.com/browser/django/trunk/django/db/models/fields/__init__.py
class VerifiableDecimalField(models.DecimalField, VerifiableField):
    # Description of this field
    description = "A verifiable decimal field"
    
    def __init__(self, verifiableId, freshness=True, *args, **kwargs):
        # Place code here, which is excecuted the same
        # time the ``pre_init``-signal would be

        #self._tree = VerifiableTree(verifiableId)
        self.verifiableId = verifiableId
        self._freshness = freshness
        self.getDataPassword()
        
        # Call parent's ``init`` function
        super(VerifiableDecimalField, self).__init__(*args,**kwargs)

        # Place code here, which is excecuted the same
        # time the ``post_init``-signal would be

# Field methods here: https://code.djangoproject.com/browser/django/trunk/django/db/models/fields/__init__.py
class VerifiableEmailField(models.EmailField, VerifiableField):
    # Description of this field
    description = "A verifiable email field"
    
    def __init__(self, verifiableId, freshness=True, *args, **kwargs):
        # Place code here, which is excecuted the same
        # time the ``pre_init``-signal would be

        #self._tree = VerifiableTree(verifiableId)
        self.verifiableId = verifiableId
        self._freshness = freshness
        self.getDataPassword()
        
        # Call parent's ``init`` function
        super(VerifiableEmailField, self).__init__(*args,**kwargs)

        # Place code here, which is excecuted the same
        # time the ``post_init``-signal would be

# Field methods here: https://code.djangoproject.com/browser/django/trunk/django/db/models/fields/__init__.py
class VerifiableFilePathField(models.FilePathField, VerifiableField):
    # Description of this field
    description = "A verifiable file path field"
    
    def __init__(self, verifiableId, freshness=True, *args, **kwargs):
        # Place code here, which is excecuted the same
        # time the ``pre_init``-signal would be

        #self._tree = VerifiableTree(verifiableId)
        self.verifiableId = verifiableId
        self._freshness = freshness
        self.getDataPassword()
        
        # Call parent's ``init`` function
        super(VerifiableFilePathField, self).__init__(*args,**kwargs)

        # Place code here, which is excecuted the same
        # time the ``post_init``-signal would be
        
# Field methods here: https://code.djangoproject.com/browser/django/trunk/django/db/models/fields/__init__.py
class VerifiableFloatField(models.FloatField, VerifiableField):
    # Description of this field
    description = "A verifiable float field"
    
    def __init__(self, verifiableId, freshness=True, *args, **kwargs):
        # Place code here, which is excecuted the same
        # time the ``pre_init``-signal would be

        #self._tree = VerifiableTree(verifiableId)
        self.verifiableId = verifiableId
        self._freshness = freshness
        self.getDataPassword()
        
        # Call parent's ``init`` function
        super(VerifiableFloatField, self).__init__(*args,**kwargs)

        # Place code here, which is excecuted the same
        # time the ``post_init``-signal would be
        
# Field methods here: https://code.djangoproject.com/browser/django/trunk/django/db/models/fields/__init__.py
class VerifiableIntegerField(models.IntegerField, VerifiableField):
    # Description of this field
    description = "A verifiable integer field"
    
    def __init__(self, verifiableId, freshness=True, *args, **kwargs):
        # Place code here, which is excecuted the same
        # time the ``pre_init``-signal would be

        #self._tree = VerifiableTree(verifiableId)
        self.verifiableId = verifiableId
        self._freshness = freshness
        self.getDataPassword()
        
        # Call parent's ``init`` function
        super(VerifiableIntegerField, self).__init__(*args,**kwargs)

        # Place code here, which is excecuted the same
        # time the ``post_init``-signal would be
        
# Field methods here: https://code.djangoproject.com/browser/django/trunk/django/db/models/fields/__init__.py
class VerifiableBigIntegerField(models.BigIntegerField, VerifiableField):
    # Description of this field
    description = "A verifiable big integer field"
    
    def __init__(self, verifiableId, freshness=True, *args, **kwargs):
        # Place code here, which is excecuted the same
        # time the ``pre_init``-signal would be

        #self._tree = VerifiableTree(verifiableId)
        self.verifiableId = verifiableId
        self._freshness = freshness
        self.getDataPassword()
        
        # Call parent's ``init`` function
        super(VerifiableBigIntegerField, self).__init__(*args,**kwargs)

        # Place code here, which is excecuted the same
        # time the ``post_init``-signal would be

# Field methods here: https://code.djangoproject.com/browser/django/trunk/django/db/models/fields/__init__.py
class VerifiableIPAddressField(models.IPAddressField, VerifiableField):
    # Description of this field
    description = "A verifiable IP address field"
    
    def __init__(self, verifiableId, freshness=True, *args, **kwargs):
        # Place code here, which is excecuted the same
        # time the ``pre_init``-signal would be

        #self._tree = VerifiableTree(verifiableId)
        self.verifiableId = verifiableId
        self._freshness = freshness
        self.getDataPassword()
        
        # Call parent's ``init`` function
        super(VerifiableIPAddressField, self).__init__(*args,**kwargs)

        # Place code here, which is excecuted the same
        # time the ``post_init``-signal would be
        
# Field methods here: https://code.djangoproject.com/browser/django/trunk/django/db/models/fields/__init__.py
class VerifiableNullBooleanField(models.NullBooleanField, VerifiableField):
    # Description of this field
    description = "A verifiable null boolean field"
    
    def __init__(self, verifiableId, freshness=True, *args, **kwargs):
        # Place code here, which is excecuted the same
        # time the ``pre_init``-signal would be

        #self._tree = VerifiableTree(verifiableId)
        self.verifiableId = verifiableId
        self._freshness = freshness
        self.getDataPassword()
        
        # Call parent's ``init`` function
        super(VerifiableNullBooleanField, self).__init__(*args,**kwargs)

        # Place code here, which is excecuted the same
        # time the ``post_init``-signal would be
        
# Field methods here: https://code.djangoproject.com/browser/django/trunk/django/db/models/fields/__init__.py
class VerifiablePositiveIntegerField(models.PositiveIntegerField, VerifiableField):
    # Description of this field
    description = "A verifiable positive integer field"
    
    def __init__(self, verifiableId, freshness=True, *args, **kwargs):
        # Place code here, which is excecuted the same
        # time the ``pre_init``-signal would be

        #self._tree = VerifiableTree(verifiableId)
        self.verifiableId = verifiableId
        self._freshness = freshness
        self.getDataPassword()
        
        # Call parent's ``init`` function
        super(VerifiablePositiveIntegerField, self).__init__(*args,**kwargs)

        # Place code here, which is excecuted the same
        # time the ``post_init``-signal would be
        
# Field methods here: https://code.djangoproject.com/browser/django/trunk/django/db/models/fields/__init__.py
class VerifiablePositiveSmallIntegerField(models.PositiveSmallIntegerField, VerifiableField):
    # Description of this field
    description = "A verifiable positive small integer field"
    
    def __init__(self, verifiableId, freshness=True, *args, **kwargs):
        # Place code here, which is excecuted the same
        # time the ``pre_init``-signal would be

        #self._tree = VerifiableTree(verifiableId)
        self.verifiableId = verifiableId
        self._freshness = freshness
        self.getDataPassword()
        
        # Call parent's ``init`` function
        super(VerifiablePositiveSmallIntegerField, self).__init__(*args,**kwargs)

        # Place code here, which is excecuted the same
        # time the ``post_init``-signal would be

# Field methods here: https://code.djangoproject.com/browser/django/trunk/django/db/models/fields/__init__.py
class VerifiableSlugField(models.SlugField, VerifiableField):
    # Description of this field
    description = "A verifiable slug field"
    
    def __init__(self, verifiableId, freshness=True, *args, **kwargs):
        # Place code here, which is excecuted the same
        # time the ``pre_init``-signal would be

        #self._tree = VerifiableTree(verifiableId)
        self.verifiableId = verifiableId
        self._freshness = freshness
        self.getDataPassword()
        
        # Call parent's ``init`` function
        super(VerifiableSlugField, self).__init__(*args,**kwargs)

        # Place code here, which is excecuted the same
        # time the ``post_init``-signal would be
        
# Field methods here: https://code.djangoproject.com/browser/django/trunk/django/db/models/fields/__init__.py
class VerifiableSmallIntegerField(models.SmallIntegerField, VerifiableField):
    # Description of this field
    description = "A verifiable slug field"
    
    def __init__(self, verifiableId, freshness=True, *args, **kwargs):
        # Place code here, which is excecuted the same
        # time the ``pre_init``-signal would be

        #self._tree = VerifiableTree(verifiableId)
        self.verifiableId = verifiableId
        self._freshness = freshness
        self.getDataPassword()
        
        # Call parent's ``init`` function
        super(VerifiableSlugField, self).__init__(*args,**kwargs)

        # Place code here, which is excecuted the same
        # time the ``post_init``-signal would be
        
# Field methods here: https://code.djangoproject.com/browser/django/trunk/django/db/models/fields/__init__.py
class VerifiableTextField(models.TextField, VerifiableField):
    # Description of this field
    description = "A verifiable text field"
    
    def __init__(self, verifiableId, freshness=True, *args, **kwargs):
        # Place code here, which is excecuted the same
        # time the ``pre_init``-signal would be

        #self._tree = VerifiableTree(verifiableId)
        self.verifiableId = verifiableId
        self._freshness = freshness
        self.getDataPassword()
        
        # Call parent's ``init`` function
        super(VerifiableTextField, self).__init__(*args,**kwargs)

        # Place code here, which is excecuted the same
        # time the ``post_init``-signal would be

# Field methods here: https://code.djangoproject.com/browser/django/trunk/django/db/models/fields/__init__.py
class VerifiableTimeField(models.TimeField, VerifiableField):
    # Description of this field
    description = "A verifiable time field"
    
    def __init__(self, verifiableId, freshness=True, *args, **kwargs):
        # Place code here, which is excecuted the same
        # time the ``pre_init``-signal would be

        #self._tree = VerifiableTree(verifiableId)
        self.verifiableId = verifiableId
        self._freshness = freshness
        self.getDataPassword()
        
        # Call parent's ``init`` function
        super(VerifiableTimeField, self).__init__(*args,**kwargs)

        # Place code here, which is excecuted the same
        # time the ``post_init``-signal would be
        
# Field methods here: https://code.djangoproject.com/browser/django/trunk/django/db/models/fields/__init__.py
class VerifiableURLField(models.URLField, VerifiableField):
    # Description of this field
    description = "A verifiable URL field"
    
    def __init__(self, verifiableId, freshness=True, *args, **kwargs):
        # Place code here, which is excecuted the same
        # time the ``pre_init``-signal would be

        #self._tree = VerifiableTree(verifiableId)
        self.verifiableId = verifiableId
        self._freshness = freshness
        self.getDataPassword()
        
        # Call parent's ``init`` function
        super(VerifiableURLField, self).__init__(*args,**kwargs)

        # Place code here, which is excecuted the same
        # time the ``post_init``-signal would be
        
'''# Field methods here: https://code.djangoproject.com/browser/django/trunk/django/db/models/fields/__init__.py
class VerifiableXMLField(models.XMLField, VerifiableField):
    # Description of this field
    description = "A verifiable XML field"
    
    def __init__(self, verifiableId, freshness=True, *args, **kwargs):
        # Place code here, which is excecuted the same
        # time the ``pre_init``-signal would be

        #self._tree = VerifiableTree(verifiableId)
        self.verifiableId = verifiableId
        self._freshness = freshness
        self.getDataPassword()
        
        # Call parent's ``init`` function
        super(VerifiableXMLField, self).__init__(*args,**kwargs)

        # Place code here, which is excecuted the same
        # time the ``post_init``-signal would be'''

# Model methods here: https://code.djangoproject.com/browser/django/trunk/django/db/models/base.py
# Model handles the init, save, and delete operations
class VerifiableModel(models.Model):
    # The hash of the row, used for integrity checking
    _data_hash = models.CharField(max_length=1024)
    
    # The HMAC password for this model
    _data_password = None
    
    # An ID for this object, for retrieving the password
    verifiableId = None

    # Set the manager to our new verifiable manager
    objects = VerifiableManager()
    
    # Required for subclassing models
    class Meta:
        abstract = True
   
    def __init__(self, *args, **kwargs):
        # Place code here, which is excecuted the same
        # time the ``pre_init``-signal would be

        # Call parent's ``init`` function
        super(VerifiableModel, self).__init__(*args,**kwargs)
        # Get the password for this model
        self.getDataPassword()

        # Place code here, which is excecuted the same
        # time the ``post_init``-signal would be
        
    def save(self, force_insert=False, force_update=False, using=None):
        # Place code here, which is excecuted the same
        # time the ``pre_save``-signal would be
        
        # Get the password if not already retrieved
        if self._data_password is None:
            self.getDataPassword()
        # Re-HMAC the row
        curr_hmac = hmac.new(self._data_password)
        # Iterate over all fields
        for field in sorted(self._meta.fields):
            # Don't use excluded fields
            if excludedField(field.name):
                continue
            # Might be taking this out, placed elsewhere.  TODO: Figure this out when tree is ready
            if isinstance(field, VerifiableField):
                pass
                #!@!field._tree.update(field.verifiableId, field.value_from_object(self))
            # Add to HMAC
            curr_hmac.update(str(getattr(self, field.name)))
        # Store new HMAC
        setattr(self, "_data_hash", curr_hmac.hexdigest())

        # Call parent's ``save`` function
        super(VerifiableModel, self).save(force_insert, force_update, using)

        # Place code here, which is excecuted the same
        # time the ``post_save``-signal would be
        
    def delete(self, using=None):
        # Place code here, which is excecuted the same
        # time the ``pre_delete``-signal would be
        
        # Need to refresh.  If had reference to object before, it may have staled.
        self = type(self).objects.get_query_set().filter(id__exact=self.id, VERIFY=False)[0]
        
        # Need to remove row from completeness
        # Iterate over the fields
        for field in sorted(self._meta.fields):
            # Don't use excluded fields
            if excludedField(field.name):
                continue
            # Check if field is verifiable
            if isinstance(field, VerifiableField):
                # If using faster completeness (no freshness)
                if field._freshness == False:
                    # Get password if not retrieved
                    if field._data_password is None:
                        field.getDataPassword()
                    # If this is the only row, just update self, no other rows.
                    if (type(self).objects.get_query_set().exclude(id__exact=self.id, VERIFY=False).count() == 0):
                        setattr(self, "_" + field.verifiableId + "_PREV", "None")
                        setattr(self, "_" + field.verifiableId + "_NEXT", "None")
                        setattr(self, "_" + field.verifiableId + "_HASH", "None")
                    # If there are other rows
                    else:
                        # Remove current row from chain
                        prev = getattr(self, "_" + field.verifiableId + "_PREV")
                        next = getattr(self, "_" + field.verifiableId + "_NEXT")
                        # If current row is first
                        if prev == 'None':
                            # Get the next row
                            kwargs = {
                                '%s__%s' % ("_" + field.verifiableId + "_PREV", 'exact'): self.id,
                                '%s' % ('VERIFY'): False
                            }
                            rows = type(self).objects.get_query_set().filter(**kwargs)
                            # If there is another row
                            if rows.count() > 0:
                                # Set PREV and HASH for first row (it is now first)
                                row = type(self).objects.get_query_set().filter(**kwargs)[0]
                                setattr(row, "_" + field.verifiableId + "_PREV", "None")
                                curr_hmac = hmac.new(field._data_password)
                                curr_hmac.update("None")
                                curr_hmac.update(str(row.id))
                                curr_hmac.update(str(getattr(row, "_" + field.verifiableId + "_NEXT")))
                                setattr(row, "_" + field.verifiableId + "_HASH", curr_hmac.hexdigest())
                                row.save()
                        # If not first
                        else:
                            # Get the prev row
                            kwargs = {
                                '%s__%s' % ("_" + field.verifiableId + "_NEXT", 'exact'): self.id,
                                '%s' % ('VERIFY'): False
                            }
                            rows = type(self).objects.get_query_set().filter(**kwargs)
                            # If there is a row before
                            if rows.count() > 0:
                                row = type(self).objects.get_query_set().filter(**kwargs)[0]
                                # Set PREV to current rows PREV
                                setattr(row, "_" + field.verifiableId + "_NEXT", str(getattr(self, "_" + field.verifiableId + "_NEXT")))
                                row.save()
                                # Set HASH of next row using new PREV value
                                curr_hmac = hmac.new(field._data_password)
                                curr_hmac.update(str(getattr(row, "_" + field.verifiableId + "_PREV")))
                                curr_hmac.update(str(row.id))
                                curr_hmac.update(str(getattr(row, "_" + field.verifiableId + "_NEXT")))
                                setattr(row, "_" + field.verifiableId + "_HASH", str(curr_hmac.hexdigest()))
                                row.save()
                            
                            # Get the next row
                            kwargs = {
                                '%s__%s' % ("_" + field.verifiableId + "_PREV", 'exact'): self.id,
                                '%s' % ('VERIFY'): False
                            }
                            rows = type(self).objects.get_query_set().filter(**kwargs)
                            # If there is a row after
                            if rows.count() > 0:
                                row = type(self).objects.get_query_set().filter(**kwargs)[0]
                                # Set PREV to current rows PREV
                                setattr(row, "_" + field.verifiableId + "_PREV", str(getattr(self, "_" + field.verifiableId + "_PREV")))
                                row.save()
                                # Set HASH of next row using new PREV value
                                curr_hmac = hmac.new(field._data_password)
                                curr_hmac.update(str(getattr(row, "_" + field.verifiableId + "_PREV")))
                                curr_hmac.update(str(row.id))
                                curr_hmac.update(str(getattr(row, "_" + field.verifiableId + "_NEXT")))
                                setattr(row, "_" + field.verifiableId + "_HASH", str(curr_hmac.hexdigest()))
                                row.save()
                # If using completeness with freshness
                else:
                    pass
                    #!@!field._tree.delete(field.verifiableId, field.value_from_object(self))

        # Call parent's ``delete`` function
        super(VerifiableModel, self).delete(using)

        # Place code here, which is excecuted the same
        # time the ``post_delete``-signal would be
        
    def getDataPassword(self):
        # Retrieve the models HMAC password
        # Creates database if doesn't exist
        conn = sqlite3.connect('verifiable.sqlite')
        c = conn.cursor()
        # Make sure table exists
        c.execute("create table if not exists model_passwords(model_name text primary key, password text)")
        # Get the list of models passwords
        c.execute("select * from model_passwords where model_name = ?", (self.verifiableId,))
        data = c.fetchone()
        # Password not set
        if data == None:
            # Create one and insert it
            self._data_password = str(random.getrandbits(256))
            if self.verifiableId == None:
                raise NoVerifiableIdError()
            c.execute("insert into model_passwords values(?,?)", (self.verifiableId, self._data_password,))
            conn.commit()
        # Password is set
        else:
            # Store it
            self._data_password = data[1]
        c.close()
        conn.close()
        
