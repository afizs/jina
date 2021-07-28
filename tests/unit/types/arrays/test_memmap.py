import os

import pytest

from jina import Document, DocumentArray
from jina.types.arrays.memmap import DocumentArrayMemmap
from tests import random_docs


def test_memmap_append_extend(tmpdir):
    dam = DocumentArrayMemmap(tmpdir)
    docs = list(random_docs(100))
    assert len(dam) == 0
    for d in docs[:40]:
        dam.append(d)
    assert len(dam) == 40
    for d1, d2 in zip(docs[:40], dam):
        assert d1.proto == d2.proto
    dam.extend(docs[40:])
    assert len(dam) == 100
    for d1, d2 in zip(docs, dam):
        assert d1.proto == d2.proto


@pytest.mark.parametrize('idx1, idx99', [(1, 99), ('id_1', 'id_99')])
def test_memmap_delete_clear(tmpdir, mocker, idx1, idx99):
    dam = DocumentArrayMemmap(tmpdir)
    candidates = list(random_docs(100))
    for d in candidates:
        d.id = f'id_{d.id}'
    dam.extend(candidates)
    assert len(dam) == 100
    del dam[idx1]
    assert len(dam) == 99
    del dam[idx99]
    assert len(dam) == 98
    for d in dam:
        assert d.id != idx1
        assert d.id != idx99
    dam.clear()
    assert len(dam) == 0
    mock = mocker.Mock()
    for _ in dam:
        mock()
    mock.assert_not_called()


@pytest.mark.parametrize('idx1, idx99', [(1, 99), ('id_1', 'id_99')])
def test_get_set_item(tmpdir, idx1, idx99):
    dam = DocumentArrayMemmap(tmpdir)
    candidates = list(random_docs(100))
    for d in candidates:
        d.id = f'id_{d.id}'
    dam.extend(candidates)
    dam[idx1] = Document(text='hello')
    assert len(dam) == 100
    with pytest.raises(IndexError):
        dam[100] = Document(text='world')
    dam[idx99] = Document(text='world')
    assert len(dam) == 100
    assert dam[1].text == 'hello'
    assert dam[99].text == 'world'
    for idx, d in enumerate(dam):
        if idx == 1:
            assert d.text == 'hello'
        if idx == 99:
            assert d.text == 'world'
    dam['unknown_new'] = Document()
    assert len(dam) == 101


def test_traverse(tmpdir, mocker):
    dam = DocumentArrayMemmap(tmpdir)
    dam.extend(random_docs(100))
    mock = mocker.Mock()
    for c in dam.traverse_flat(['c']):
        assert c.granularity == 1
        mock()
    mock.assert_called()


@pytest.mark.parametrize('content_field', ['embedding', 'text'])
def test_get_attributes(tmpdir, content_field):
    dam = DocumentArrayMemmap(tmpdir)
    dam.extend(random_docs(100))
    contents, docs = dam.get_attributes_with_docs(content_field)
    assert len(contents) == 100
    assert len(docs) == 100


def test_error(tmpdir):
    dam = DocumentArrayMemmap(tmpdir)
    dam.clear()
    with pytest.raises(KeyError):
        dam['12']
    with pytest.raises(IndexError):
        dam[1]
    with pytest.raises(IndexError):
        del dam[1]
    with pytest.raises(KeyError):
        del dam['12']


def test_persist(tmpdir):
    dam = DocumentArrayMemmap(tmpdir)
    docs = list(random_docs(100))
    for doc in docs:
        doc.scores['score'] = 50
        doc.evaluations['eval'] = 100

    dam.extend(docs)

    dam2 = DocumentArrayMemmap(tmpdir)
    assert len(dam2) == 100

    assert dam == dam2

    for d1, d2 in zip(dam, dam2):
        assert d1.proto == d2.proto

    assert '1' in dam

    del dam['1']
    assert len(dam2) == 100
    dam2.reload()
    assert len(dam2) == 99
    for doc2 in dam2:
        assert doc2.scores['score'].value == 50
        assert doc2.evaluations['eval'].value == 100

    dam.clear()
    assert len(dam2) == 99
    dam2.reload()
    assert len(dam2) == 0


def test_prune_save_space(tmpdir):
    dam = DocumentArrayMemmap(tmpdir)
    dam.extend(random_docs(100))
    old_hsize = os.stat(os.path.join(tmpdir, 'header.bin')).st_size
    old_bsize = os.stat(os.path.join(tmpdir, 'body.bin')).st_size
    del dam['2']
    dam.prune()
    new_hsize = os.stat(os.path.join(tmpdir, 'header.bin')).st_size
    new_bsize = os.stat(os.path.join(tmpdir, 'body.bin')).st_size
    assert new_bsize < old_bsize
    assert new_hsize < old_hsize


def test_convert_dam_to_da(tmpdir, mocker):
    dam = DocumentArrayMemmap(tmpdir)
    dam.extend(random_docs(100))
    da = DocumentArray(dam)
    dam.clear()
    mock = mocker.Mock()
    for d in da:
        assert d
        mock()
    mock.assert_called()
    assert len(da) == 100
    assert len(dam) == 0


def test_convert_dm_to_dam(tmpdir, mocker):
    dam = DocumentArrayMemmap(tmpdir)
    da = DocumentArray(random_docs(100))
    dam.extend(da)
    da.clear()
    mock = mocker.Mock()
    for d in dam:
        assert d
        mock()
    mock.assert_called()
    assert len(da) == 0
    assert len(dam) == 100


@pytest.mark.parametrize('embed_dim', [10, 10000])
def test_extend_and_get_attribute(tmpdir, embed_dim):
    dam = DocumentArrayMemmap(tmpdir)
    docs = list(random_docs(100, start_id=0, embed_dim=embed_dim))
    dam.extend(docs)

    dam2 = DocumentArrayMemmap(tmpdir)
    x = dam2.get_attributes('embedding')
    assert len(dam2) == 100

    docs = list(random_docs(100, start_id=100, embed_dim=embed_dim))
    dam2.extend(docs)
    x = dam2.get_attributes('embedding')
    assert len(x) == 200
    assert x[0].shape == (embed_dim,)
    assert len(dam2) == 200


def test_sample(tmpdir):
    da = DocumentArrayMemmap(tmpdir)
    docs = list(random_docs(100))
    da.extend(docs)
    sampled = da.sample(5)
    assert len(sampled) == 5
    assert isinstance(sampled, DocumentArray)
    with pytest.raises(ValueError):
        da.sample(101)


def test_sample_with_seed(tmpdir):
    da = DocumentArrayMemmap(tmpdir)
    docs = list(random_docs(100))
    da.extend(docs)
    sampled_1 = da.sample(5, seed=1)
    sampled_2 = da.sample(5, seed=1)
    sampled_3 = da.sample(5, seed=2)
    assert len(sampled_1) == len(sampled_2) == len(sampled_3) == 5
    assert sampled_1 == sampled_2
    assert sampled_1 != sampled_3


def test_shuffle(tmpdir):
    da = DocumentArrayMemmap(tmpdir)
    docs = list(random_docs(100))
    da.extend(docs)
    shuffled = da.shuffle()
    assert len(shuffled) == len(da)
    assert isinstance(shuffled, DocumentArray)
    ids_before_shuffle = [d.id for d in da]
    ids_after_shuffle = [d.id for d in shuffled]
    assert ids_before_shuffle != ids_after_shuffle
    assert sorted(ids_before_shuffle) == sorted(ids_after_shuffle)


def test_shuffle_with_seed(tmpdir):
    da = DocumentArrayMemmap(tmpdir)
    docs = list(random_docs(100))
    da.extend(docs)
    shuffled_1 = da.shuffle(seed=1)
    shuffled_2 = da.shuffle(seed=1)
    shuffled_3 = da.shuffle(seed=2)
    assert len(shuffled_1) == len(shuffled_2) == len(shuffled_3) == len(da)
    assert shuffled_1 == shuffled_2
    assert shuffled_1 != shuffled_3


def test_memmap_delete_by_slice(tmpdir):
    dam = DocumentArrayMemmap(tmpdir)
    candidates = list(random_docs(100))
    for d in candidates:
        d.id = f'id_{d.id}'
    dam.extend(candidates)
    assert len(dam) == 100
    del dam[-5:]
    assert len(dam) == 95
    del dam[:5]
    assert len(dam) == 90

    for candidate in candidates[:5] + candidates[-5:]:
        for d in dam:
            assert d.id != candidate.id


def test_memmap_get_by_slice(tmpdir):
    def _assert_similar(da1, da2):
        for doc_a, doc_b in zip(da1, da2):
            assert doc_a.id == doc_b.id

    dam = DocumentArrayMemmap(tmpdir)
    candidates = list(random_docs(100))
    for d in candidates:
        d.id = f'id_{d.id}'
    dam.extend(candidates)
    assert len(dam) == 100

    first_10 = dam[:10]
    assert len(first_10) == 10
    _assert_similar(candidates[:10], first_10)

    last_10 = dam[-10:]
    assert len(last_10) == 10
    _assert_similar(candidates[-10:], last_10)

    out_of_bound_1 = dam[-101:-95]
    assert len(out_of_bound_1) == 5
    _assert_similar(candidates[0:5], out_of_bound_1)

    out_of_bound_2 = dam[-101:101]
    assert len(out_of_bound_2) == 100
    _assert_similar(candidates, out_of_bound_2)

    out_of_bound_3 = dam[95:101]
    assert len(out_of_bound_3) == 5
    _assert_similar(candidates[95:], out_of_bound_3)

    assert len(dam[101:105]) == 0

    assert len(dam[-105:-101]) == 0

    assert len(dam[10:0]) == 0


def test_memmap_update_document(tmpdir):
    dam = DocumentArrayMemmap(tmpdir)
    candidates = list(random_docs(100))
    dam.extend(candidates)
    for idx, candidate in enumerate(candidates):
        candidate.content = f'new content {idx}'
        dam[idx] = candidate

    for idx, doc in enumerate(dam):
        assert doc.content == f'new content {idx}'
