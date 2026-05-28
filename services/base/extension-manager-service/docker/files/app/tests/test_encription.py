def test_encription():
    from v1.services import encryption

    username = "test"
    password = "password"

    encrypted = encryption.encrypt(username, password)

    decrypted = encryption.decrypt(encrypted)

    assert decrypted.get("username") == username
    assert decrypted.get("password") == password
