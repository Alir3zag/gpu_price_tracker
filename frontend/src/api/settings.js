import client from './client'

export const getSettings = () =>
  client.get('/settings')

export const updateSettings = (data) =>
  client.patch('/settings', data)
