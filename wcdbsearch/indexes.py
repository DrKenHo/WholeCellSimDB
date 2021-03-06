'''
Whole-cell knowledge base haystack indices

Author: Jonathan Karr, jkarr@stanford.edu
Affiliation: Covert Lab, Department of Bioengineering, Stanford University
Last updated: 2012-07-17
'''

from haystack import site
from haystack.indexes import CharField, IntegerField, SearchIndex, ModelSearchIndex
from helpers import truncate_fields
from wcdb import models

class OrganismIndex(SearchIndex):
    text = CharField(document=True, use_template=True)
    
    name = CharField(model_attr='name')
    
    # Hack to avoid error: "xapian.InvalidArgumentError: Term too long (> 245)"
    # See: https://groups.google.com/forum/?fromgroups#!topic/django-haystack/hRJKcPNPXqw
    def prepare(self, object):
        self.prepared_data = truncate_fields(super(OrganismIndex, self).prepare(object))        
        return self.prepared_data
        
    class Meta:
        pass
        
class SimulationBatchIndex(SearchIndex):
    text = CharField(document=True, use_template=True)
    
    name = CharField(model_attr='name')
    description = CharField(model_attr='description')
    
    # Hack to avoid error: "xapian.InvalidArgumentError: Term too long (> 245)"
    # See: https://groups.google.com/forum/?fromgroups#!topic/django-haystack/hRJKcPNPXqw
    def prepare(self, object):
        self.prepared_data = truncate_fields(super(SimulationBatchIndex, self).prepare(object))        
        return self.prepared_data
            
    class Meta:
        pass        
        
class InvestigatorIndex(SearchIndex):
    text = CharField(document=True, use_template=True)
    
    first_name = CharField(model_attr='user__first_name')
    last_name = CharField(model_attr='user__last_name')
    affiliation = CharField(model_attr='affiliation')
    
    def prepare(self, object):
        self.prepared_data = truncate_fields(super(InvestigatorIndex, self).prepare(object))        
        return self.prepared_data
            
    class Meta:
        pass

#register indices
site.register(models.Organism, OrganismIndex)
site.register(models.SimulationBatch, SimulationBatchIndex)
#site.register(models.Simulation, SimulationIndex)
site.register(models.Investigator, InvestigatorIndex)