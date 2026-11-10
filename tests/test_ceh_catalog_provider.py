import json

import pytest

from contentos.ceh_catalog import main, recommend
from test_ceh_contract import catalog, entry


def test_disabled_provider_does_not_read_or_change_defaults(tmp_path):
    result = recommend(path=tmp_path / 'missing.json', task='kinetic typography')
    assert not result['available'] and result['selected'] == []


def test_trusted_provider_selects_metadata_and_rejects_missing_requirements(entry, tmp_path):
    doc = catalog(entry)
    path = tmp_path / 'catalog.json'
    path.write_text(json.dumps(doc))
    args = dict(path=path, enabled=True, expected_digest=doc['digest'], task='kinetic typography')
    missing = recommend(**args)
    assert not missing['selected'] and missing['rejected']
    result = recommend(**args, environment={'runtimes': {'node': '22.0.0'},
        'dependencies': {'hyperframes': '0.8.114'}, 'inputs': {'title': 'Hello'}})
    assert result['selected'][0]['renderer'] == 'hyperframes'
    assert 'metadata only' in result['execution']


@pytest.mark.parametrize('environment', [{'runtimes':42}, {'inputs':42}, {'bad':True}])
def test_programmatic_environment_failure_is_safe(entry, tmp_path, environment):
    doc = catalog(entry)
    path = tmp_path / 'catalog.json'
    path.write_text(json.dumps(doc))
    result = recommend(path=path, enabled=True, expected_digest=doc['digest'], task='kinetic typography', environment=environment)
    assert result['selected'] == []


def test_cli_disabled_and_missing_catalog(capsys):
    assert main(['--task','kinetic typography']) == 0
    assert not json.loads(capsys.readouterr().out)['available']
    assert main(['--enable','--task','kinetic typography']) == 1
    assert json.loads(capsys.readouterr().out)['errors']
