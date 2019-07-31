from ba_data_paths import ba_data


def test_get_child_keys():
    key_lst = ba_data._get_child_keys(r'SOFTWARE\WOW6432Node\Esri\BusinessAnalyst\Datasets\USA_ESRI_2018')
    assert(len(key_lst))


def test_usa_key():
    reg_key = ba_data._get_first_child_key(r'SOFTWARE\WOW6432Node\Esri\BusinessAnalyst\Datasets', 'USA_ESRI')
    assert(isinstance(reg_key, str))


def test_get_business_analyst_key_value():
    reg_key = ba_data._get_business_analyst_key_value('DataInstallDir')
    assert(isinstance(reg_key, str))


def test_data_install_dir():
    dir_path = ba_data.usa_data_path
    assert(isinstance(dir_path, str))


def test_locator_install_dir():
    dir_path = ba_data.usa_locator
    assert(isinstance(dir_path, str))


def test_network_install_dir():
    dir_path = ba_data.usa_network_dataset
    assert(isinstance(dir_path, str))
