import os

import numpy as np
import nibabel as nib
from sklearn.neighbors import KNeighborsClassifier
import pycartool

def open_text(fname):
    with open(fname) as file:
        lines = file.readlines()
        keep_rois = list()
        for line in lines:
            roi_name = line.strip()
            keep_rois.append(roi_name)
    return(keep_rois)


def open_lut(fname):
    # open lut
    dtype = [('id', '<i8'), ('name', 'U47'),
             ('R', '<i8'), ('G', '<i8'), ('B', '<i8'), ('A', '<i8')]
    data_lut = np.genfromtxt(fname, dtype=dtype)
    palette = np.zeros((data_lut['id'][-1] + 1, 3))
    for k, id in enumerate(data_lut['id']):
        palette[id] = [data_lut['R'][k],
                       data_lut['G'][k],
                       data_lut['B'][k]]
    return(data_lut, palette)


def create_region_of_interest(mri, spi, data_lut, keep_rois):
    # Convert MRI to 3D
    if mri.get_fdata().ndim == 3:
        mri_data = np.round(mri.get_fdata()).astype(int)
    elif mri.get_fdata().ndim == 4:
        mri_data = np.round(mri.get_fdata()[:, :, :, 0]).astype(int)
    # Project coordinates to MRI space
    coordinates = spi.coordinates
    origin = np.array([mri.header['qoffset_x'],
                       mri.header['qoffset_y'],
                       mri.header['qoffset_z']])
    s_coordinates = np.array([np.array(c) - origin for c in coordinates.tolist()])
    sources_indices = np.arange(0, len(coordinates))
    # Generate MRI data
    training_pos = list()
    training_labels = list()
    for i in range(0, mri_data.shape[0]):
        for j in range(0, mri_data.shape[1]):
            for k in range(0, mri_data.shape[2]):
                if mri_data[i, j, k] > 0:
                    training_pos.append([i+0.5, j+0.5, k+0.5])
                    training_labels.append(mri_data[i, j, k])
    # train classifier
    knn = KNeighborsClassifier(n_neighbors=5, metric='euclidean')
    knn.fit(np.array(training_pos), np.array(training_labels).astype(int))
    # predict source labels
    source_labels = knn.predict(s_coordinates)

    # Exclude sources far from labels
    good_indices = np.all(knn.kneighbors(s_coordinates)[0] < 5, axis=1)
    good_coord = s_coordinates[good_indices]
    good_labels = source_labels[good_indices]
    good_indices = sources_indices[good_indices]
    # Create Rois
    if keep_rois is not None:
        names = keep_rois
        keep_labels = [data_lut['id'][np.where(data_lut['name'] == roi_name)][0] for roi_name in names]
        groups_of_indices = list()
        for l,label in enumerate(keep_labels):
            if len(list(good_indices[np.where(good_labels == label)])) == 0:
                raise ValueError(f'No source found in {names[l]}')
            groups_of_indices.append(list(good_indices[np.where(good_labels == label)]))
    else:
        names = list()
        groups_of_indices = list()
        for label in np.unique(good_labels):
            names.append(data_lut['name'][np.where(data_lut['id'] == label)][0])
            groups_of_indices.append(list(good_indices[np.where(good_labels == label)]))
        print(names)

    rois = pycartool.regions_of_interest.RegionsOfInterest(names,
                                                            groups_of_indices,
                                                            source_space=spi)

    sources_mri = np.zeros(mri_data.shape)
    for coord, indice in zip(good_coord.astype(int), good_labels):
        sources_mri[coord[0], coord[1], coord[2]] = int(indice)
    img = nib.Nifti1Image(sources_mri.astype('uint16'), mri.affine)

    # Create rois_spi
    rois_spi_names = list()
    rois_spi_coords = list()
    for name, indexes in zip(rois.names, rois.groups_of_indexes):
        center_of_mass = np.mean(coordinates[indexes], axis=0)
        rois_spi_coords.append(center_of_mass)
        rois_spi_names.append(name)
    rois_spi = pycartool.source_space.SourceSpace(rois_spi_names,
                                                np.array(rois_spi_coords),
                                                subject=None, filename=None)
    return(rois, img, rois_spi)


def save_rois(rois, fname):
    # Save
    with open(fname, 'w') as the_file:
        the_file.write('RO01' + '\n')
        the_file.write(str((rois.source_space.n_sources)) + '\n')
        the_file.write(str(len(rois.groups_of_indexes)) + '\n')
        for i in range(0, len(rois.groups_of_indexes)):
            the_file.write(rois.names[i] + '\n')
            for ind in rois.groups_of_indexes[i]:
                the_file.write(str(ind + 1) + ' ')
            the_file.write('\n')
