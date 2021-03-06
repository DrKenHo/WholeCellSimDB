'''
Example: 
>> python wcdbcli/convert_mat_to_hdf5.py \
     -o "Mycoplasma genitalium" \
     -n "Wild-type set #1" \
     -d /home/projects/WholeCell/simulation/output/runSimulation/2011_10_19_02_53_45/1 \
     -i 1
'''

import argparse
import h5py
import numpy
import os
import re
import scipy.io
import subprocess
import sys
import tempfile
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))

from WholeCellDB import settings

def main():
    parser = argparse.ArgumentParser(description='Save batch of simulations to database.')
    parser.add_argument('-o', metavar='organism', help='Name of organism', required=True)
    parser.add_argument('-n', metavar='name', help='Name of simulation batch', required=True)
    parser.add_argument('-d', metavar='directory', help='Path to directory containing simulation data and metadata', required=True)
    parser.add_argument('-i', metavar='batch-index', type=int, help='Index of simulation within batch', required=True)
    parser.add_argument('-m', metavar='mcr-path', default='/usr/local/bin/MATLAB/MATLAB_Compiler_Runtime/v81', help='Path to MATLAB MCR')
    parser.add_argument('-e', metavar='expand-sparse-mat', type=bool, default=True, help='True/false indicating whether or not to expand sparse matrices')
    parser.add_argument('-t', metavar='tmp-path', default=settings.TMP_DIR, help='Path to temporary directory')
    args = parser.parse_args()
    
    organism = args.o
    name = args.n
    sim_dir = args.d
    batch_index = args.i
    path_to_mcr = args.m
    expand_sparse_mat = args.e
    tmp_dir = args.t
    
    excluded_properties = ['Metabolite/processAllocations', 'Metabolite/processRequirements', 'Metabolite/processUsages']
    
    #create h5 file
    h5file = h5py.File('%s.h5' % sim_dir, 'w')
    
    #load metadata
    md = scipy.io.loadmat(os.path.join(sim_dir, 'metadata.mat'))
    h5file.attrs['batch__organism__name'] = organism
    h5file.attrs['batch__organism_version'] = str(md['revision'][0][0])
    h5file.attrs['batch__name'] = name
    h5file.attrs['batch__description'] = str(md['longDescription'][0])
    h5file.attrs['batch__investigator__user__first_name'] = str(md['firstName'][0])
    h5file.attrs['batch__investigator__user__last_name'] = str(md['lastName'][0])
    h5file.attrs['batch__investigator__user__email'] = str(md['email'][0])
    h5file.attrs['batch__investigator__affiliation'] = str(md['affiliation'][0])
    h5file.attrs['batch__ip'] = str(md['ipAddress'][0])
    h5file.attrs['batch__date'] = str(md['startTime'][0])
    h5file.attrs['batch_index'] = batch_index
    h5file.attrs['length'] = md['lengthSec'][0][0]
    
    #options
    options = load_options(sim_dir)
    group = h5file.create_group('options')
    for prop_name, val in options.iteritems():
        if prop_name == 'processes' or prop_name == 'states':
            continue
        if isinstance(val['value'], dict):
            val['value'] = str(val['value'])
        dset = group.create_dataset(prop_name, data=str(val['value'] or ''))
        dset.attrs['units'] = str(val['units'] or '')
    
    sub_group = group.create_group('processes')
    for process_name, props in options['processes'].iteritems():
        sub_sub_group = sub_group.create_group(process_name)
        for prop_name, val in props.iteritems():
            if isinstance(val['value'], dict):
                val['value'] = str(val['value'])
            dset = sub_sub_group.create_dataset(prop_name, data=str(val['value'] or ''))
            dset.attrs['units'] = str(val['units'] or '')
    
    sub_group = group.create_group('states')
    for state_name, props in options['states'].iteritems():
        sub_sub_group = sub_group.create_group(state_name)
        for prop_name, val in props.iteritems():
            if isinstance(val['value'], dict):
                val['value'] = str(val['value'])
            dset = sub_sub_group.create_dataset(prop_name, data=str(val['value'] or ''))
            dset.attrs['units'] = str(val['units'] or '')
    
    #parameters
    parameters = load_parameters(sim_dir)
    group = h5file.create_group('parameters')
    for prop_name, val in parameters.iteritems():
        if prop_name == 'processes' or prop_name == 'states':
            continue
        if isinstance(val['value'], dict):
            val['value'] = str(val['value'])
        dset = group.create_dataset(prop_name, data=str(val['value'] or ''))
        dset.attrs['units'] = str(val['units'] or '')
    
    sub_group = group.create_group('processes')
    for process_name, props in parameters['processes'].iteritems():
        sub_sub_group = sub_group.create_group(process_name)
        for prop_name, val in props.iteritems():
            if isinstance(val['value'], dict):
                val['value'] = str(val['value'])
            dset = sub_sub_group.create_dataset(prop_name, data=str(val['value'] or ''))
            dset.attrs['units'] = str(val['units'] or '')
    
    sub_group = group.create_group('states')
    for state_name, props in parameters['states'].iteritems():
        sub_sub_group = sub_group.create_group(state_name)
        for prop_name, val in props.iteritems():
            if isinstance(val['value'], dict):
                val['value'] = str(val['value'])
            dset = sub_sub_group.create_dataset(prop_name, data=str(val['value'] or ''))
            dset.attrs['units'] = str(val['units'] or '')
    
    #processes
    group = h5file.create_group('processes')
    for process_name in parameters['processes'].keys():
        group.create_group(process_name)
    
    #flush
    h5file.flush()
    
    #load states
    states = load_states(sim_dir)
    
    for state_name, props in states.iteritems():
        sys.stdout.write('Saving %s ...\n' % state_name)
        sys.stdout.flush()
        
        for prop_name, units_labels in props.iteritems():
            sys.stdout.write('  %s ... ' % prop_name)
            sys.stdout.flush()
            
            h5file.create_group('states/%s/%s' % (state_name, prop_name))
            
            filename = os.path.join(sim_dir, 'state-%s-%s.mat' % (state_name, prop_name))
            load_property_status = load_property(filename, h5file, state_name, prop_name, excluded_properties, expand_sparse_mat, tmp_dir, path_to_mcr)                
                
            h5file.create_dataset(
                'states/%s/%s/units' % (state_name, prop_name),
                data = str(units_labels['units'] or ''))
                
            h5file.create_group('states/%s/%s/labels' % (state_name, prop_name))
            for dim, dim_labels in enumerate(units_labels['labels'] or []):
                h5file.create_dataset(
                    'states/%s/%s/labels/%d' % (state_name, prop_name, dim),
                    data = [str(x) for x in dim_labels])
            
            #flush h5 file to disk
            h5file.flush()
            
            if load_property_status:
                sys.stdout.write('done\n')
            else:
                sys.stdout.write('unable to load data\n')
            sys.stdout.flush()
    
    #save h5 file
    h5file.close()
    
def load_options(sim_dir):
    units_labels = loadmat(os.path.join(sim_dir, 'units_labels.mat'))
    option_vals = loadmat(os.path.join(sim_dir, 'options.mat'))
    
    options = {}
    for prop_name, value in option_vals.iteritems():
        if re.match(r"^__.+?__$", prop_name) or prop_name == 'processes' or prop_name == 'states':
            continue
        options[prop_name] = {
            'units': units_labels[prop_name]['units'] if prop_name in units_labels and 'units' in units_labels[prop_name] else None, 
            'value': value
            }
    options['processes'] = {}
    for process_name, props in option_vals['processes'].iteritems():
        options['processes'][process_name] = {}
        for prop_name, value in props.iteritems():
            options['processes'][process_name][prop_name] = {
                'units': units_labels['processes'][process_name][prop_name]['units'] if process_name in units_labels['processes'] and prop_name in units_labels['processes'][process_name] and 'units' in units_labels['processes'][process_name][prop_name] else None, 
                'value': value
                }
    options['states'] = {}
    for state_name, props in option_vals['states'].iteritems():
        options['states'][state_name] = {}
        for prop_name, value in props.iteritems():
            options['states'][state_name][prop_name] = {
                'units': units_labels['states'][state_name][prop_name]['units'] if state_name in units_labels['states'] and prop_name in units_labels['states'][state_name] and 'units' in units_labels['states'][state_name][prop_name] else None, 
                'value': value
                }
    
    return options

def load_parameters(sim_dir):
    units_labels = loadmat(os.path.join(sim_dir, 'units_labels.mat'))
    parameter_vals = loadmat(os.path.join(sim_dir,  'parameters.mat'))
    
    parameters = {}
    for prop_name, value in parameter_vals.iteritems():
        if re.match(r"^__.+?__$", prop_name) or prop_name == 'processes' or prop_name == 'states':
            continue
        
        parameters[prop_name] = {
            'units': units_labels[prop_name]['units'] if prop_name in units_labels and 'units' in units_labels[prop_name] else None,
            'value': value
            }
    parameters['processes'] = {}
    for process_name, props in parameter_vals['processes'].iteritems():
        parameters['processes'][process_name] = {}
        for prop_name, value in props.iteritems():
            parameters['processes'][process_name][prop_name] = {
                'units': units_labels['processes'][process_name][prop_name]['units'] if process_name in units_labels['processes'] and prop_name in units_labels['processes'][process_name] and 'units' in units_labels['processes'][process_name][prop_name] else None, 
                'value': value
                }
    parameters['states'] = {}
    for state_name, props in parameter_vals['states'].iteritems():
        parameters['states'][state_name] = {}
        for prop_name, value in props.iteritems():
            parameters['states'][state_name][prop_name] = {
                'units': units_labels['states'][state_name][prop_name]['units'] if state_name in units_labels['states'] and prop_name in units_labels['states'][state_name] and 'units' in units_labels['states'][state_name][prop_name] else None, 
                'value': value
                }
    
    return parameters

def load_states(sim_dir):
    units_labels = loadmat(os.path.join(sim_dir, 'units_labels.mat'))
    
    states = {}
    for state_name, state in loadmat(os.path.join(sim_dir, 'state-0.mat'), False).iteritems():
        states[state_name] = {}
        for prop_name, prop_value in state.iteritems():
            if state_name in units_labels['states'] and \
                prop_name in units_labels['states'][state_name] and \
                'units' in units_labels['states'][state_name][prop_name]:
                units = units_labels['states'][state_name][prop_name]['units']
            else:
                units = None
            if state_name in units_labels['states'] and \
                prop_name in units_labels['states'][state_name] and \
                'labels' in units_labels['states'][state_name][prop_name]:
                labels = []
                for dim_labels in units_labels['states'][state_name][prop_name]['labels']:
                    if dim_labels.size > 0:
                        tmp = dim_labels[0].tolist()
                        labels.append([x[0] if x.size > 0 else '' for x in tmp])
                    else:
                        labels.append([])
            else:
                labels = None
            states[state_name][prop_name] = {'units': units, 'labels': labels}
    
    return states
    
def load_property(filename, h5file, state_name, prop_name, excluded_properties, expand_sparse_mat, tmp_dir, path_to_mcr):
    if not os.path.isfile(filename):
        return False
    
    try:
        mat_data = scipy.io.loadmat(filename)
        
        if 'data' in mat_data:
            dset = h5file.create_dataset(
                'states/%s/%s/data' % (state_name, prop_name),
                data = mat_data['data'],
                compression = "gzip",
                compression_opts = 4, 
                chunks = True)
        elif 'None' in mat_data and \
            expand_sparse_mat and \
            isinstance(mat_data['None'], scipy.io.matlab.mio5_params.MatlabOpaque) and \
            mat_data['None'].tolist()[0][2] == 'edu.stanford.covert.util.SparseMat' and \
            ('%s/%s' % (state_name, prop_name)) not in excluded_properties:
            
            tmp_filedescriptor, tmp_filename = tempfile.mkstemp(dir=tmp_dir, suffix='.mat')
            tmp_file = os.fdopen(tmp_filedescriptor, 'w')
            tmp_file.close()
            os.remove(tmp_filename)
            tmp_filename_h5 = tmp_filename.replace('.mat', '.h5')
            
            compiled_matlab_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'expand_sparse_mat', 'run_expand_sparse_mat.sh')
            devnull = open('/dev/null', 'w')
            subprocess.call([compiled_matlab_path, path_to_mcr, filename, tmp_filename, tmp_filename_h5], stdout=devnull, stderr=devnull)
            
            try:
                if os.path.isfile(tmp_filename):
                    mat_data = scipy.io.loadmat(tmp_filename)
                    if 'data' in mat_data:
                        dset = h5file.create_dataset(
                            'states/%s/%s/data' % (state_name, prop_name),
                            data = mat_data['data'],
                            compression = "gzip",
                            compression_opts = 4, 
                            chunks = True)
                elif os.path.isfile(tmp_filename_h5):
                    h5_data = h5py.File(tmp_filename_h5, 'r')
                    if 'data' in h5_data:
                        dset = h5file.create_dataset(
                            'states/%s/%s/data' % (state_name, prop_name),
                            data = h5_data['data'],
                            compression = "gzip",
                            compression_opts = 4, 
                            chunks = True)
                    h5_data.close()
                else:
                    return False
            except:
                return False
                
            if os.path.isfile(tmp_filename):
                os.remove(tmp_filename)
            if os.path.isfile(tmp_filename_h5):
                os.remove(tmp_filename_h5)
    except NotImplementedError:
        return False
        
    return True

def loadmat(filename, throw_error_on_unknown_data_format=True):
    data = scipy.io.loadmat(filename, struct_as_record=False)
    dict = {}
    for key in data:
        if isinstance(data[key], numpy.ndarray):
            if len(data[key]) == 1 and \
               isinstance(data[key][0], numpy.ndarray) and len(data[key][0]) == 1 and \
               isinstance(data[key][0][0], scipy.io.matlab.mio5_params.mat_struct):
                dict[key] = _normalize(data[key][0][0], throw_error_on_unknown_data_format)
            elif data[key].ndim == 1 and isinstance(data[key][0], numpy.unicode_):
                dict[key] = data[key].tolist()[0]
            elif data[key].ndim == 2 and data[key].shape[0] == 1 and data[key].shape[1] == 1:
                dict[key] = data[key].tolist()[0][0]
    return dict

def _normalize(matobj, throw_error_on_unknown_data_format):
    '''
    A recursive function which constructs from matobjects nested dictionaries
    '''
    dict = {}
    for strg in matobj._fieldnames:
        elem = matobj.__dict__[strg]
        if isinstance(elem, numpy.ndarray) and len(elem) == 1 and \
           isinstance(elem[0], numpy.ndarray) and len(elem[0]) == 1 and \
           isinstance(elem[0][0], scipy.io.matlab.mio5_params.mat_struct):
            dict[strg] = _normalize(elem[0][0], throw_error_on_unknown_data_format)
        else:
            if elem.ndim == 1 and isinstance(elem[0], numpy.unicode_):
                dict[strg] = elem.tolist()[0]
            elif elem.ndim == 2 and elem.shape[0] == 1 and elem.shape[1] == 1:
                dict[strg] = elem.tolist()[0][0]
            elif elem.ndim == 2 and elem.shape[0] == 1:
                dict[strg] = elem.tolist()[0]
            elif elem.ndim == 2 and elem.shape[1] == 1:
                dict[strg] = [x[0] for x in elem.tolist()]
            elif elem.ndim == 2 and elem.shape[0] == 0 and elem.shape[1] == 0:
                dict[strg] = None
            elif throw_error_on_unknown_data_format:
                raise Exception('Invalid data')
            else:
                dict[strg] = elem
    
    return dict

if __name__=="__main__":
    main()