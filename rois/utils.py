import os

import numpy as np
import nibabel as nib
from sklearn.neighbors import KNeighborsClassifier
import pycartool


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


def create_region_of_interest(mri, spi, data_lut, palette, fname_spi=None):
    # Convert MRI to 3D
    if mri.get_data().ndim == 3:
        source_data = mri.get_data()
    elif mri.get_data().ndim == 4:
        source_data = mri.get_data()[:, :, :, 0]
    # Project coordinates to MRI space
    coordinates = spi.coordinates
    origin = np.array([mri.header['qoffset_x'],
                       mri.header['qoffset_y'],
                       mri.header['qoffset_z']])
    s_coordinates = np.array([np.array(c) - origin for c in coordinates.tolist()])
    sources_indices = np.arange(0, len(coordinates))
    # Generate MRI data
    mri_data = source_data
    training_pos = list()
    training_labels = list()
    for i in range(0, mri_data.shape[0]):
        for j in range(0, mri_data.shape[1]):
            for k in range(0, mri_data.shape[2]):
                if mri_data[i, j, k] != 0:
                    training_pos.append([i+0.5, j+0.5, k+0.5])
                    training_labels.append(mri_data[i, j, k])
    # train classifier
    knn = KNeighborsClassifier(n_neighbors=5, metric='euclidean')
    knn.fit(np.array(training_pos), np.array(training_labels))
    # predict source labels
    source_labels = knn.predict(s_coordinates)

    # Exclude sources far from labels
    good_indices = np.all(knn.kneighbors(s_coordinates)[0] < 5, axis=1)
    good_coord = s_coordinates[good_indices]
    good_labels = source_labels[good_indices]
    good_indices = sources_indices[good_indices]

    # Create Rois
    names = list()
    groups_of_indices = list()

    for label in set(good_labels):
        names.append(data_lut['name'][np.where(data_lut['id'] == label)])
        groups_of_indices.append(list(good_indices[np.where(good_labels == label)]))

    rois = pycartool.regions_of_interest.RegionsOfInterest(names,
                                                           groups_of_indices,
                                                           source_space=spi)

    sources_mri = np.zeros(source_data.shape)
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
    with open(fname, 'a') as the_file:
        the_file.write('RO01' + '\n')
        the_file.write(str((rois.source_space.n_sources)) + '\n')
        the_file.write(str(len(rois.groups_of_indexes)) + '\n')
        for i in range(0, len(rois.groups_of_indexes)):
            the_file.write(rois.names[i][0] + '\n')
            for ind in rois.groups_of_indexes[i]:
                the_file.write(str(ind + 1) + ' ')
            the_file.write('\n')
