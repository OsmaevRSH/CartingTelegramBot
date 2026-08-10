def test_exchange_rejects_unknown_code(client):
    response = client.post('/api/mobile/auth/exchange', json={'code': '12345678'})

    assert response.status_code == 401
    assert response.json() == {'detail': 'Недействительный или истёкший код'}
