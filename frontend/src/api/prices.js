import client from './client'

export const getPrices = (params = {}) =>
  client.get('/prices', { params })

export const getPriceHistory = (name) =>
  client.get('/prices/history', { params: { name } })

export const triggerScrape = () =>
  client.post('/scrape')
