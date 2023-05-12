from seafileapi.client import SeafileApiClient
from seafileapi.files import SeafDir, SeafFile
from seafileapi.repo import Repo, RepoRevision
from seafileapi.repos import Repos
from seafileapi.exceptions import DoesNotExist, OperationError, ClientHttpError


def connect(server, username, password):
    client = SeafileApiClient(server, username, password)
    return client
