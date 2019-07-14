import random
import time
from enum import Enum
from typing import List
from subprocess import Popen, PIPE
from shlex import split
from memory_profiler import profile
import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm

from sklearn.pipeline import Pipeline
from sklearn.model_selection import GridSearchCV
from scipy.cluster.hierarchy import dendrogram
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA
from sklearn import metrics

from sklearn.cluster import DBSCAN, AgglomerativeClustering, AffinityPropagation, SpectralClustering, OPTICS
from .pyclustering_wrapper import KMeansWrapper, KMediansWrapper, KMedoidsWrapper, ExpectationMaximizationWrapper, \
    BSASWrapper, MBSASWrapper, TTSASWrapper, RockWrapper, SOMSCWrapper
import hdbscan
from concept_formation import cobweb3, trestle

BASE = "/home/fabian/Nextcloud/workspace/uni/8/bachelor_project"
CACHE_PATH = "/tmp/"


# Restructure into pipeline:
#   1. generate/sample
#   2. load data
#   3. preprocess data
#   4. Cluster data
#   5. Evaluate
#   6. Visualize


class Dataset(Enum):
    SYNTHETIC = (BASE + "/data/synthetic.json", BASE + "/data/synthetic.tree")
    NOISY_SYNTHETIC = (BASE + "/data/synthetic_noisy.json", BASE + "/data/synthetic.tree")
    YELP = (BASE + "/data/business.json", BASE + "/data/business.tree")


def generate_synthetic(depth: int, width: int = 2, path: str = BASE + "/data/", rem_labels: bool = True,
                       add_labels: bool = False, alter_labels: bool = True, prob: float = 0.33):
    command = "java -jar " + BASE + "/lib/synthetic_data_generator.jar -p '" + path + "' -d " + str(
        depth) + " -w " + str(width) \
              + " -n " + str(rem_labels) + " " + str(add_labels) + " " + str(alter_labels) + " -pr " + str(prob)
    args = split(command)
    Popen(args)


def sample_yelp(n_samples: int) -> List[List[str]]:
    sample = []
    with open(Dataset.YELP.value[0], "r") as read_file:
        for i, line in enumerate(read_file):
            if i < n_samples:
                sample.append(json.loads(line))
            elif i >= n_samples and random.random() < n_samples / float(i + 1):
                replace = random.randint(0, len(sample) - 1)
                sample[replace] = json.loads(line)

        labels = [entry['categories'] for entry in sample]

        labels = [label for label in labels if label is not None]

    return [labels]


def open_synthetic(noisy: bool):
    path = Dataset.SYNTHETIC.value[0] if noisy else Dataset.NOISY_SYNTHETIC.value[0]
    with open(path, "r") as read_file:
        data = json.load(read_file)

    labels = [entry['labels'] for entry in data]

    return labels


def load(n_samples: int, dataset: Dataset) -> List[List[str]]:
    if dataset == Dataset.SYNTHETIC or Dataset.NOISY_SYNTHETIC:
        generate_synthetic(int(n_samples / 2))
        noisy = True if dataset == Dataset.NOISY_SYNTHETIC else False
        return open_synthetic(noisy)
    else:
        return sample_yelp(n_samples)


# TODO add robust single linkage/condensed tree
# average, complete, single
def cluster_agglomerative():
    return {'agglo_clusterer': AgglomerativeClustering(affinity='jaccard', linkage='complete', memory=CACHE_PATH)}  # ,
    # 'n_clusters': [1, 2, 4, 8, 16, 32, 64, int(0.001 * n_samples) + 1, int(0.01 * n_samples) + 1,
    # int(0.1 * n_samples) + 1, int(0.2 * n_samples) + 1, 0.3 * n_samples],
    # 'linkage': ['single', 'average', 'complete']}


def cluster_affinity_prop():
    return {'pre_clusterer': AffinityPropagation(affinity='precomputed')}


def cluster_spectral():
    return {'pre_clusterer': SpectralClustering(affinity='precomputed', n_jobs=-1)}


def cluster_dbscan():
    return {'pre_clusterer': DBSCAN(metric='precomputed', n_jobs=-1)}


def cluster_optics():
    return {'pre_clusterer': OPTICS()}


def cluster_kmeans():
    return {'pre_clusterer': KMeansWrapper(n_clusters=5)}


def cluster_kmedoids():
    return {'pre_clusterer': KMedoidsWrapper(n_clusters=5)}


def cluster_kmedians():
    return {'pre_clusterer': KMediansWrapper(n_clusters=5)}


def cluster_em():
    return {'pre_clusterer': ExpectationMaximizationWrapper(n_clusters=5)}


def cluster_bsas():
    return {'pre_clusterer': BSASWrapper(max_n_clusters=5)}


def cluster_mbsas():
    return {'pre_clusterer': MBSASWrapper(max_n_clusters=5)}


def cluster_ttsas():
    return {'pre_clusterer': TTSASWrapper(max_n_clusters=5)}


def cluster_rock():
    return {'pre_clusterer': RockWrapper(n_clusters=5)}


def cluster_som():
    return {'pre_clusterer': SOMSCWrapper(n_clusters=5)}


# TODO API for End-to-End approaches: 1. fit, 2. flat clusters, 3. tree
def cluster_hdbscan():
    return {'end-to-end_clusterer': hdbscan.HDBSCAN(metric='precomputed', memory=CACHE_PATH, core_dist_n_jobs=-1)}


def cluster_trestle():
    start_time = time.time()
    time_taken = time.time() - start_time
    # concept formation
    raise NotImplementedError


def cluster_cobweb_3():
    start_time = time.time()
    time_taken = time.time() - start_time
    # concept formation
    raise NotImplementedError


@profile
def bench_estimator(estimator, params, data):
    start_time = time.time()
    result = estimator(params).fit(data)
    time_taken = time.time() - start_time

    return result, time_taken


# In: result of clustering, Out: results of TED
def compute_ted(linkage_tree: np.array, dataset: Dataset) -> int:
    # apted
    # FIXME load .tree for groundtruth and generate bracket tree for result from child array

    groundtruth_tree = dataset
    result_tree = create_bracket_tree_from_dendrogram(linkage_tree)
    command = "java -jar apted.jar -t " + str(groundtruth_tree) + " " + result_tree
    args = split(command)
    with Popen(args, stdout=PIPE) as apted:
        return int(apted.stdout.read().decode("utf-8"))


# in: preproc. data, out: result of cv as accuracy
def cross_validate():
    raise NotImplementedError


def create_bracket_tree_from_dendrogram(children: np.array):
    raise NotImplementedError


def visualize_dendro(children: np.array, labels: np.array, distance: np.array, path: str):
    no_of_observations = np.arange(2, children.shape[0] + 2)
    # FIXME adjust distance: is it right like that
    linkage_matrix = np.column_stack([children, distance, no_of_observations]).astype(float)

    plt.title('Hierarchical Clustering Dendrogram')
    dendrogram(linkage_matrix, labels=labels)
    plt.show()
    plt.savefig(path + "Dendrogram.svg")


# TODO Refactor and find way to visualize all kinds propperly
def visualize_clusters(path: str, labels: np.array, projected_data: np.array):
    n_clusters_ = len(set(labels)) - (1 if -1 in labels else 0)
    unique_labels = set(labels)
    cmap = cm.get_cmap("Spectral")
    colors = [cmap(each) for each in np.linspace(0, 1, len(unique_labels))]

    plt.figure()
    for k, col in zip(unique_labels, colors):
        if k == -1:
            # Black used for noise.
            col = [0, 0, 0, 1]

        class_member_mask = (labels == k)

        xy = projected_data[class_member_mask]
        plt.plot(xy[:, 0], xy[:, 1], 'o', markerfacecolor=tuple(col),
                 markeredgecolor='k', markersize=10)

    plt.title('Number of clusters: %d' % n_clusters_)
    plt.savefig(path + "Clusters.svg")
    plt.show()
    # # DBSCAN Plotting and measures
    # core_samples_mask = np.zeros_like(db.labels_, dtype=bool)
    # core_samples_mask[db.core_sample_indices_] = True
    # labels = db.labels_
    #
    # # Number of clusters in labels, ignoring noise if present.
    # n_clusters_ = len(set(labels)) - (1 if -1 in labels else 0)
    # n_noise_ = list(labels).count(-1)
    #
    # print('Estimated number of clusters: %d' % n_clusters_)
    # print('Estimated number of noise points: %d' % n_noise_)
    # print("Silhouette Coefficient: %0.3f"
    #       % metrics.silhouette_score(transformed_data, labels))
    #
    # unique_labels = set(labels)
    # cmap = cm.get_cmap("Spectral")
    # colors = [cmap(each)
    #           for each in np.linspace(0, 1, len(unique_labels))]
    # for k, col in zip(unique_labels, colors):
    #     if k == -1:
    #         # Black used for noise.
    #         col = [0, 0, 0, 1]
    #
    #     class_member_mask = (labels == k)
    #
    #     xy = projected_data[class_member_mask & core_samples_mask]
    #     plt.plot(xy[:, 0], xy[:, 1], 'o', markerfacecolor=tuple(col),
    #              markeredgecolor='k', markersize=14)
    #
    #     xy = projected_data[class_member_mask & ~core_samples_mask]
    #     plt.plot(xy[:, 0], xy[:, 1], 'o', markerfacecolor=tuple(col),
    #              markeredgecolor='k', markersize=6)
    #
    # plt.title('DBSCAN: Estimated number of clusters: %d' % n_clusters_)
    # plt.savefig(IMG_PATH + "dbscan_clusters.svg")
    # plt.show()
    # plt.title('Hierarchical Clustering Dendrogram')
    #
    # children = agglo.children_
    #
    # # Distances between each pair of children
    # # Since we don't have this information, we can use a uniform one for plotting
    # distance = np.arange(children.shape[0])
    #
    # # The number of observations contained in each cluster level
    # no_of_observations = np.arange(2, children.shape[0] + 2)
    #
    # # Create linkage matrix and then plot the dendrogram
    # linkage_matrix = np.column_stack([children, distance, no_of_observations]).astype(float)
    #
    # # Plot the corresponding dendrogram
    # dendrogram(linkage_matrix, labels=birch.labels_)
    # plt.savefig(IMG_PATH + "agglo_dendro.svg")
    #
    # plt.figure()
    # labels = birch.labels_
    # n_clusters_ = len(set(labels)) - (1 if -1 in labels else 0)
    # unique_labels = set(labels)
    # cmap = cm.get_cmap("Spectral")
    # colors = [cmap(each)
    #           for each in np.linspace(0, 1, len(unique_labels))]
    #
    # for k, col in zip(unique_labels, colors):
    #     if k == -1:
    #         # Black used for noise.
    #         col = [0, 0, 0, 1]
    #
    #     class_member_mask = (labels == k)
    #
    #     xy = transformed_data[class_member_mask]
    #     plt.plot(xy[:, 0], xy[:, 1], 'o', markerfacecolor=tuple(col),
    #              markeredgecolor='k', markersize=10)
    #
    # plt.title('BIRCH + Agglo: Estimated number of clusters: %d' % n_clusters_)
    # plt.savefig(IMG_PATH + "agglo_clust.svg")
    # plt.show()
    # labels = hdb.labels_
    #
    # # Number of clusters in labels, ignoring noise if present.
    # n_clusters_ = len(set(labels)) - (1 if -1 in labels else 0)
    # n_noise_ = list(labels).count(-1)
    #
    # print('Estimated number of clusters: %d' % n_clusters_)
    # print('Estimated number of noise points: %d' % n_noise_)
    # print("Silhouette Coefficient: %0.3f"
    #       % metrics.silhouette_score(transformed_data, labels))
    # print("Cluster  stability per cluster:")
    # for val in hdb.cluster_persistence_:
    #     print("\t %0.3f" % val)
    #
    # unique_labels = set(labels)
    # cmap = cm.get_cmap("Spectral")
    # colors = [cmap(each)
    #           for each in np.linspace(0, 1, len(unique_labels))]
    # for k, col in zip(unique_labels, colors):
    #     if k == -1:
    #         # Black used for noise.
    #         col = [0, 0, 0, 1]
    #
    #     class_member_mask = (labels == k)
    #
    #     xy = projected_data[class_member_mask]
    #     plt.plot(xy[:, 0], xy[:, 1], 'o', markerfacecolor=tuple(col),
    #              markeredgecolor='k', markersize=14)
    #
    #     xy = projected_data[class_member_mask]
    #     plt.plot(xy[:, 0], xy[:, 1], 'o', markerfacecolor=tuple(col),
    #              markeredgecolor='k', markersize=6)
    # plt.title('HDBSCAN*: Estimated number of clusters: %d' % n_clusters_)
    # plt.savefig(IMG_PATH + str(i) + "hdbscan_clusters.svg")
    # plt.show()
    # plt.figure()
    # hdb.single_linkage_tree_.plot()
    # plt.savefig(IMG_PATH + str(i) + "hdbscan_dendro.svg")
    # plt.show()
    # plt.figure()
    # hdb.condensed_tree_.plot()
    # plt.savefig(IMG_PATH + str(i) + "hdbscan_condensed.svg")
    # plt.show()


def transform_numeric(vectorized_data: np.array) -> np.array:
    transformed_data = np.array(vectorized_data)
    pca_data = PCA(n_components=0.7, svd_solver='full').fit_transform(transformed_data)
    tsne_data = TSNE(metric='jaccard').fit_transform(pca_data)

    return tsne_data


def main(n_samples: int, dataset: Dataset):
    print("Generating/Sampling and loading data")
    data = load(n_samples, dataset)
    vectorized_data = CountVectorizer(binary=True).fit(data)

    distance_matrix = metrics.pairwise_distances(vectorized_data, metric='jaccard', n_jobs=-1)

    # Case 1: Plain Agglomerative Clustering and End-to-End approaches
    print("Loading finished, starting to cluster")
    pipeline = Pipeline([
        ('to-tree', 'passthrough')
    ])
    params = cluster_agglomerative()
    searcher = GridSearchCV(pipeline, param_grid=params, cv=3, n_jobs=-1, n_iter=20,
                            scoring=[metrics.calinski_harabaz_score, metrics.silhouette_score], refit=True)

    searcher.fit(vectorized_data)
    estimator = searcher.best_estimator_
    params = searcher.best_params_
    result, time_taken = bench_estimator(estimator, params, distance_matrix)
    print(time_taken)

    # Case 2: Pipeline of 2 algos: first standard clustering, then agglomerative
    pipe = Pipeline([
        ('pre_clusterer', 'passthrough'),
        ('agglo_clusterer', 'passthrough')
    ])
    grid_params = [cluster_kmeans(), cluster_kmedians(), cluster_kmedoids(), cluster_bsas(), cluster_mbsas(),
                   cluster_ttsas(), cluster_em(), cluster_affinity_prop(), cluster_spectral(), cluster_rock(),
                   cluster_dbscan(), cluster_optics(), cluster_som(), cluster_agglomerative()]
    searcher = GridSearchCV(pipe, param_grid=grid_params, cv=3, n_jobs=-1,
                            scoring=[metrics.calinski_harabaz_score, metrics.silhouette_score], refit=True)

    searcher.fit(distance_matrix)
    estimator = searcher.best_estimator_
    params = searcher.best_params_
    result, time_taken = bench_estimator(estimator, params, vectorized_data)
    print(time_taken)


if __name__ == '__main__':
    main(1000, Dataset.SYNTHETIC)