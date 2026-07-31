"""S3 support tests, using moto's mocked S3 rather than live AWS -- exercises
the same boto3 code paths (S3Store, s3_client, open_s3/save_s3) against a
fake-but-behaviorally-real S3 server, so these are true integration tests of
the S3 read/write paths, not just of S3Location's URL parsing.
"""

import shutil
from pathlib import Path

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

import marspylib.yama as yama
from marspylib.yama.s3 import S3Location, resolve_s3_location

FIXTURES = Path(__file__).parent / "fixtures"
SINGLE_FILE = FIXTURES / "yama" / "single_molecule_archive.yama"
STORE_DIR = FIXTURES / "yama_store" / "single_molecule_archive.yama.store"

BUCKET = "my-bucket"
SERVER_ADDRESS = "s3.amazonaws.com"


@pytest.fixture(autouse=True)
def aws_credentials(monkeypatch):
    # moto intercepts every request, so these never touch real AWS -- they
    # just need to be *present* so botocore is willing to sign requests.
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


@pytest.fixture
def bucket():
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=BUCKET)
        yield client


def _upload_directory(client, local_dir: Path, key_prefix: str) -> None:
    for path in local_dir.rglob("*"):
        if path.is_file():
            rel = path.relative_to(local_dir).as_posix()
            client.upload_file(str(path), BUCKET, f"{key_prefix}/{rel}")


# -- S3Location / resolve_s3_location -----------------------------------

def test_location_combined_url_round_trip():
    url = "https://my-bucket.s3.serveraddress/path/to/file.yama"
    location = S3Location.from_url(url)
    assert location.bucket == "my-bucket"
    assert location.server_address == "s3.serveraddress"
    assert location.key == "path/to/file.yama"
    assert location.virtual_hosted_url == url


def test_location_combined_url_round_trip_store():
    url = "https://my-bucket.s3.serveraddress/path/to/archive.yama.store"
    location = S3Location.from_url(url)
    assert location.key == "path/to/archive.yama.store"
    assert location.virtual_hosted_url == url


def test_resolve_s3_location_requires_all_three_fields_or_a_location():
    with pytest.raises(ValueError):
        resolve_s3_location(bucket="b", key="k")
    with pytest.raises(ValueError):
        resolve_s3_location()


def test_resolve_s3_location_passes_through_existing_location():
    location = S3Location(server_address="s3.example.org", bucket="b", key="k")
    assert resolve_s3_location(location) is location


def test_resolve_s3_location_from_separate_fields():
    location = resolve_s3_location(server_address="s3.example.org", bucket="b", key="k.yama")
    assert location == S3Location(server_address="s3.example.org", bucket="b", key="k.yama")


# -- single-file .yama on S3 ---------------------------------------------

def test_open_s3_single_file_with_separate_fields(bucket):
    bucket.upload_file(str(SINGLE_FILE), BUCKET, "path/to/experiment.yama")

    archive = yama.open_s3(server_address=SERVER_ADDRESS, bucket=BUCKET,
                            key="path/to/experiment.yama")

    assert archive.properties.archive_type == "de.mpg.biochem.mars.molecule.SingleMoleculeArchive"
    assert len(archive) == 3
    assert isinstance(archive._source_path, S3Location)


def test_open_s3_single_file_with_combined_url(bucket):
    bucket.upload_file(str(SINGLE_FILE), BUCKET, "path/to/experiment.yama")

    url = f"https://{BUCKET}.{SERVER_ADDRESS}/path/to/experiment.yama"
    archive = yama.open_s3(url)

    assert len(archive) == 3
    assert archive["mol3"].tags == ["accepted", "reviewed"]


def test_save_s3_single_file_round_trip(bucket):
    archive = yama.open(SINGLE_FILE)
    archive["mol1"].add_tag("s3_edited")

    archive.save_s3(server_address=SERVER_ADDRESS, bucket=BUCKET, key="out/experiment.yama")

    reopened = yama.open_s3(server_address=SERVER_ADDRESS, bucket=BUCKET, key="out/experiment.yama")
    assert reopened["mol1"].tags == ["accepted", "s3_edited"]
    assert len(reopened) == 3


def test_save_s3_no_args_reuses_open_location(bucket):
    bucket.upload_file(str(SINGLE_FILE), BUCKET, "path/to/experiment.yama")
    archive = yama.open_s3(server_address=SERVER_ADDRESS, bucket=BUCKET,
                            key="path/to/experiment.yama")

    archive["mol2"].parameters["new_param"] = 4.5
    archive.save()  # no args -- should dispatch to save_s3() and reuse the location

    reopened = yama.open_s3(server_address=SERVER_ADDRESS, bucket=BUCKET,
                             key="path/to/experiment.yama")
    assert reopened["mol2"].parameters["new_param"] == 4.5


# -- .yama.store virtual archive on S3 ------------------------------------

def test_open_s3_virtual_store(bucket):
    _upload_directory(bucket, STORE_DIR, "stores/single.yama.store")

    archive = yama.open_s3(server_address=SERVER_ADDRESS, bucket=BUCKET,
                            key="stores/single.yama.store")

    assert archive.properties.number_of_molecules == 3
    assert len(archive) == 3
    mol1 = archive["mol1"]
    assert mol1.tags == ["accepted"]
    assert mol1.parameters["dwell"] == 5.5


def test_open_s3_virtual_store_predicate_pushdown_from_index(bucket):
    _upload_directory(bucket, STORE_DIR, "stores/single.yama.store")

    archive = yama.open_s3(server_address=SERVER_ADDRESS, bucket=BUCKET,
                            key="stores/single.yama.store")

    # answered from indexes.sml, without loading the full molecule record
    assert archive._molecules.tags_for("mol3") == ["accepted", "reviewed"]
    assert archive._molecules.channel_for("mol3") == 2
    assert "mol3" not in archive._molecules._cache


def test_save_s3_virtual_store_put_and_round_trip(bucket):
    _upload_directory(bucket, STORE_DIR, "stores/work.yama.store")

    archive = yama.open_s3(server_address=SERVER_ADDRESS, bucket=BUCKET,
                            key="stores/work.yama.store")
    archive["mol1"].add_tag("s3_python_edited")
    archive.save()

    reopened = yama.open_s3(server_address=SERVER_ADDRESS, bucket=BUCKET,
                             key="stores/work.yama.store")
    assert reopened["mol1"].tags == ["accepted", "s3_python_edited"]
    assert reopened["mol3"].tags == ["accepted", "reviewed"]


def test_save_s3_virtual_store_remove(bucket):
    _upload_directory(bucket, STORE_DIR, "stores/remove.yama.store")

    archive = yama.open_s3(server_address=SERVER_ADDRESS, bucket=BUCKET,
                            key="stores/remove.yama.store")
    archive.remove("mol2")
    assert len(archive) == 2

    # remove() deletes the underlying S3 object immediately, matching
    # mars-core's MoleculeArchiveAmazonS3Source semantics -- ahead of the
    # next save(), which is what rewrites indexes.sml
    with pytest.raises(ClientError):
        bucket.head_object(Bucket=BUCKET, Key="stores/remove.yama.store/Molecules/mol2.sml")

    archive.save()

    reopened = yama.open_s3(server_address=SERVER_ADDRESS, bucket=BUCKET,
                             key="stores/remove.yama.store")
    assert len(reopened) == 2
    assert "mol2" not in reopened
