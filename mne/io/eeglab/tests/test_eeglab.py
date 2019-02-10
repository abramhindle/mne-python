# Author: Mainak Jas <mainak.jas@telecom-paristech.fr>
#         Mikolaj Magnuski <mmagnuski@swps.edu.pl>
#         Stefan Appelhoff <stefan.appelhoff@mailbox.org>
#
# License: BSD (3-clause)

from copy import deepcopy
from distutils.version import LooseVersion
import os.path as op
import shutil
from unittest import SkipTest

import numpy as np
from numpy.testing import (assert_array_equal, assert_array_almost_equal,
                           assert_equal)
import pytest
from scipy import io

from mne import write_events, read_epochs_eeglab
from mne.io import read_raw_eeglab
from mne.io.tests.test_raw import _test_raw_reader
from mne.datasets import testing
from mne.utils import run_tests_if_main, requires_h5py
from mne.annotations import events_from_annotations, read_annotations


base_dir = op.join(testing.data_path(download=False), 'EEGLAB')

raw_fname_mat = op.join(base_dir, 'test_raw.set')
raw_fname_onefile_mat = op.join(base_dir, 'test_raw_onefile.set')
epochs_fname_mat = op.join(base_dir, 'test_epochs.set')
epochs_fname_onefile_mat = op.join(base_dir, 'test_epochs_onefile.set')
raw_mat_fnames = [raw_fname_mat, raw_fname_onefile_mat]
epochs_mat_fnames = [epochs_fname_mat, epochs_fname_onefile_mat]

raw_fname_h5 = op.join(base_dir, 'test_raw_h5.set')
raw_fname_onefile_h5 = op.join(base_dir, 'test_raw_onefile_h5.set')
epochs_fname_h5 = op.join(base_dir, 'test_epochs_h5.set')
epochs_fname_onefile_h5 = op.join(base_dir, 'test_epochs_onefile_h5.set')
raw_h5_fnames = [raw_fname_h5, raw_fname_onefile_h5]
epochs_h5_fnames = [epochs_fname_h5, epochs_fname_onefile_h5]

raw_fnames = [raw_fname_mat, raw_fname_onefile_mat,
              raw_fname_h5, raw_fname_onefile_h5]
montage = op.join(base_dir, 'test_chans.locs')


def _check_h5(fname):
    if fname.endswith('_h5.set'):
        try:
            import h5py  # noqa, analysis:ignore
        except Exception:
            raise SkipTest('h5py module required')


@requires_h5py
@testing.requires_testing_data
@pytest.mark.parametrize('fnames', [raw_mat_fnames, raw_h5_fnames])
def test_io_set_raw(fnames, tmpdir):
    """Test importing EEGLAB .set files."""
    tmpdir = str(tmpdir)
    raw_fname, raw_fname_onefile = fnames
    _test_raw_reader(read_raw_eeglab, input_fname=raw_fname,
                     montage=montage)
    # test that preloading works
    raw0 = read_raw_eeglab(input_fname=raw_fname, montage=montage,
                           preload=True)
    raw0.filter(1, None, l_trans_bandwidth='auto', filter_length='auto',
                phase='zero')

    # test that using uint16_codec does not break stuff
    raw0 = read_raw_eeglab(input_fname=raw_fname, montage=montage,
                           preload=False, uint16_codec='ascii')

    # test reading file with one event (read old version)
    eeg = io.loadmat(raw_fname_mat, struct_as_record=False,
                     squeeze_me=True)['EEG']

    # test negative event latencies
    negative_latency_fname = op.join(tmpdir, 'test_negative_latency.set')
    evnts = deepcopy(eeg.event[0])
    evnts.latency = 0
    io.savemat(negative_latency_fname,
               {'EEG': {'trials': eeg.trials, 'srate': eeg.srate,
                        'nbchan': eeg.nbchan,
                        'data': 'test_negative_latency.fdt',
                        'epoch': eeg.epoch, 'event': evnts,
                        'chanlocs': eeg.chanlocs, 'pnts': eeg.pnts}},
               appendmat=False, oned_as='row')
    shutil.copyfile(op.join(base_dir, 'test_raw.fdt'),
                    negative_latency_fname.replace('.set', '.fdt'))
    with pytest.warns(RuntimeWarning, match="has a sample index of -1."):
        read_raw_eeglab(input_fname=negative_latency_fname, preload=True,
                        montage=montage)
    evnts.latency = -1
    io.savemat(negative_latency_fname,
               {'EEG': {'trials': eeg.trials, 'srate': eeg.srate,
                        'nbchan': eeg.nbchan,
                        'data': 'test_negative_latency.fdt',
                        'epoch': eeg.epoch, 'event': evnts,
                        'chanlocs': eeg.chanlocs, 'pnts': eeg.pnts}},
               appendmat=False, oned_as='row')
    with pytest.raises(ValueError, match='event sample index is negative'):
        with pytest.warns(RuntimeWarning, match="has a sample index of -1."):
            read_raw_eeglab(input_fname=negative_latency_fname, preload=True,
                            montage=montage)

    # test overlapping events
    overlap_fname = op.join(tmpdir, 'test_overlap_event.set')
    io.savemat(overlap_fname,
               {'EEG': {'trials': eeg.trials, 'srate': eeg.srate,
                        'nbchan': eeg.nbchan, 'data': 'test_overlap_event.fdt',
                        'epoch': eeg.epoch,
                        'event': [eeg.event[0], eeg.event[0]],
                        'chanlocs': eeg.chanlocs, 'pnts': eeg.pnts}},
               appendmat=False, oned_as='row')
    shutil.copyfile(op.join(base_dir, 'test_raw.fdt'),
                    overlap_fname.replace('.set', '.fdt'))

    # test reading file with one channel
    one_chan_fname = op.join(tmpdir, 'test_one_channel.set')
    io.savemat(one_chan_fname,
               {'EEG': {'trials': eeg.trials, 'srate': eeg.srate,
                        'nbchan': 1, 'data': np.random.random((1, 3)),
                        'epoch': eeg.epoch, 'event': eeg.epoch,
                        'chanlocs': {'labels': 'E1', 'Y': -6.6069,
                                     'X': 6.3023, 'Z': -2.9423},
                        'times': eeg.times[:3], 'pnts': 3}},
               appendmat=False, oned_as='row')
    with pytest.warns(None) as w:
        read_raw_eeglab(input_fname=one_chan_fname, preload=True,
                        stim_channel=False)
    # no warning for 'no events found'
    assert len(w) == 0

    # test reading file with 3 channels - one without position information
    # first, create chanlocs structured array
    ch_names = ['F3', 'unknown', 'FPz']
    x, y, z = [1., 2., np.nan], [4., 5., np.nan], [7., 8., np.nan]
    dt = [('labels', 'S10'), ('X', 'f8'), ('Y', 'f8'), ('Z', 'f8')]
    nopos_dt = [('labels', 'S10'), ('Z', 'f8')]
    chanlocs = np.zeros((3,), dtype=dt)
    nopos_chanlocs = np.zeros((3,), dtype=nopos_dt)
    for ind, vals in enumerate(zip(ch_names, x, y, z)):
        for fld in range(4):
            chanlocs[ind][dt[fld][0]] = vals[fld]
            if fld in (0, 3):
                nopos_chanlocs[ind][dt[fld][0]] = vals[fld]
    # In theory this should work and be simpler, but there is an obscure
    # SciPy writing bug that pops up sometimes:
    # nopos_chanlocs = np.array(chanlocs[['labels', 'Z']])

    if LooseVersion(np.__version__) == '1.14.0':
        # There is a bug in 1.14.0 (or maybe with SciPy 1.0.0?) that causes
        # this write to fail!
        raise SkipTest('Need to fix bug in NumPy 1.14.0!')

    # save set file
    one_chanpos_fname = op.join(tmpdir, 'test_chanpos.set')
    io.savemat(one_chanpos_fname,
               {'EEG': {'trials': eeg.trials, 'srate': eeg.srate,
                        'nbchan': 3, 'data': np.random.random((3, 3)),
                        'epoch': eeg.epoch, 'event': eeg.epoch,
                        'chanlocs': chanlocs, 'times': eeg.times[:3],
                        'pnts': 3}},
               appendmat=False, oned_as='row')
    # load it
    with pytest.warns(RuntimeWarning, match='did not have a position'):
        raw = read_raw_eeglab(input_fname=one_chanpos_fname, preload=True)
    # position should be present for first two channels
    for i in range(2):
        assert_array_equal(raw.info['chs'][i]['loc'][:3],
                           np.array([-chanlocs[i]['Y'],
                                     chanlocs[i]['X'],
                                     chanlocs[i]['Z']]))
    # position of the last channel should be zero
    assert_array_equal(raw.info['chs'][-1]['loc'][:3], [np.nan] * 3)

    # test reading channel names from set and positions from montage
    with pytest.warns(RuntimeWarning, match='did not have a position'):
        raw = read_raw_eeglab(input_fname=one_chanpos_fname, preload=True,
                              montage=montage)

    # when montage was passed - channel positions should be taken from there
    correct_pos = [[-0.56705965, 0.67706631, 0.46906776], [np.nan] * 3,
                   [0., 0.99977915, -0.02101571]]
    for ch_ind in range(3):
        assert_array_almost_equal(raw.info['chs'][ch_ind]['loc'][:3],
                                  np.array(correct_pos[ch_ind]))

    # test reading channel names but not positions when there is no X (only Z)
    # field in the EEG.chanlocs structure
    nopos_fname = op.join(tmpdir, 'test_no_chanpos.set')
    io.savemat(nopos_fname,
               {'EEG': {'trials': eeg.trials, 'srate': eeg.srate, 'nbchan': 3,
                        'data': np.random.random((3, 2)), 'epoch': eeg.epoch,
                        'event': eeg.epoch, 'chanlocs': nopos_chanlocs,
                        'times': eeg.times[:2], 'pnts': 2}},
               appendmat=False, oned_as='row')
    # load the file
    raw = read_raw_eeglab(input_fname=nopos_fname, preload=True,
                          stim_channel=False)

    # test that channel names have been loaded but not channel positions
    for i in range(3):
        assert_equal(raw.info['chs'][i]['ch_name'], ch_names[i])
        assert_array_equal(raw.info['chs'][i]['loc'][:3],
                           np.array([np.nan, np.nan, np.nan]))


@pytest.mark.timeout(60)  # ~60 sec on Travis OSX
@requires_h5py
@testing.requires_testing_data
@pytest.mark.parametrize('fnames', [epochs_mat_fnames, epochs_h5_fnames])
def test_io_set_epochs(fnames):
    """Test importing EEGLAB .set epochs files."""
    epochs_fname, epochs_fname_onefile = fnames
    with pytest.warns(RuntimeWarning, match='multiple events'):
        epochs = read_epochs_eeglab(epochs_fname)
    with pytest.warns(RuntimeWarning, match='multiple events'):
        epochs2 = read_epochs_eeglab(epochs_fname_onefile)
    # one warning for each read_epochs_eeglab because both files have epochs
    # associated with multiple events
    assert_array_equal(epochs.get_data(), epochs2.get_data())


@testing.requires_testing_data
def test_io_set_epochs_events(tmpdir):
    """Test different combinations of events and event_ids."""
    tmpdir = str(tmpdir)
    out_fname = op.join(tmpdir, 'test-eve.fif')
    events = np.array([[4, 0, 1], [12, 0, 2], [20, 0, 3], [26, 0,  3]])
    write_events(out_fname, events)
    event_id = {'S255/S8': 1, 'S8': 2, 'S255/S9': 3}
    out_fname = op.join(tmpdir, 'test-eve.fif')
    epochs = read_epochs_eeglab(epochs_fname_mat, events, event_id)
    assert_equal(len(epochs.events), 4)
    assert epochs.preload
    assert epochs._bad_dropped
    epochs = read_epochs_eeglab(epochs_fname_mat, out_fname, event_id)
    pytest.raises(ValueError, read_epochs_eeglab, epochs_fname_mat,
                  None, event_id)
    pytest.raises(ValueError, read_epochs_eeglab, epochs_fname_mat,
                  epochs.events, None)


@testing.requires_testing_data
def test_degenerate(tmpdir):
    """Test some degenerate conditions."""
    # test if .dat file raises an error
    tmpdir = str(tmpdir)
    eeg = io.loadmat(epochs_fname_mat, struct_as_record=False,
                     squeeze_me=True)['EEG']
    eeg.data = 'epochs_fname.dat'
    bad_epochs_fname = op.join(tmpdir, 'test_epochs.set')
    io.savemat(bad_epochs_fname,
               {'EEG': {'trials': eeg.trials, 'srate': eeg.srate,
                        'nbchan': eeg.nbchan, 'data': eeg.data,
                        'epoch': eeg.epoch, 'event': eeg.event,
                        'chanlocs': eeg.chanlocs, 'pnts': eeg.pnts}},
               appendmat=False, oned_as='row')
    shutil.copyfile(op.join(base_dir, 'test_epochs.fdt'),
                    op.join(tmpdir, 'test_epochs.dat'))
    with pytest.warns(RuntimeWarning, match='multiple events'):
        pytest.raises(NotImplementedError, read_epochs_eeglab,
                      bad_epochs_fname)


@pytest.mark.parametrize("fname", raw_fnames)
@testing.requires_testing_data
def test_eeglab_annotations(fname):
    """Test reading annotations in EEGLAB files."""
    _check_h5(fname)
    annotations = read_annotations(fname)
    assert len(annotations) == 154
    assert set(annotations.description) == {'rt', 'square'}
    assert np.all(annotations.duration == 0.)


@testing.requires_testing_data
def test_eeglab_read_annotations():
    """Test annotations onsets are timestamps (+ validate some)."""
    annotations = read_annotations(raw_fname_mat)
    validation_samples = [0, 1, 2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31]
    expected_onset = np.array([1.00, 1.69, 2.08, 4.70, 7.71, 11.30, 17.18,
                               20.20, 26.12, 29.14, 35.25, 44.30, 47.15])
    assert annotations.orig_time is None
    assert_array_almost_equal(annotations.onset[validation_samples],
                              expected_onset, decimal=2)


@testing.requires_testing_data
def test_eeglab_event_from_annot():
    """Test all forms of obtaining annotations."""
    base_dir = op.join(testing.data_path(download=False), 'EEGLAB')
    raw_fname_mat = op.join(base_dir, 'test_raw.set')
    raw_fname = raw_fname_mat
    montage = op.join(base_dir, 'test_chans.locs')
    event_id = {'rt': 1, 'square': 2}
    raw1 = read_raw_eeglab(input_fname=raw_fname, montage=montage,
                           preload=False)

    annotations = read_annotations(raw_fname)
    assert len(raw1.annotations) == 154
    raw1.set_annotations(annotations)
    events_b, _ = events_from_annotations(raw1, event_id=event_id)
    assert len(events_b) == 154


run_tests_if_main()
