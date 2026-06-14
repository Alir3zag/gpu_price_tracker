import client from './client'

export const register = (email, password) =>
  client.post('/auth/register', { email, password })

export const login = (email, password) => {
  const form = new URLSearchParams()
  form.append('username', email)
  form.append('password', password)
  return client.post('/auth/login', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
}

export const getMe = () =>
  client.get('/auth/me')
