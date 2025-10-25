import { useState } from 'react'
import { Send, ExternalLink, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import './App.css'

interface Image {
  url: string
  width: number | null
  height: number | null
  alt: string | null
}

interface ProductItem {
  title: string
  normalized_title: string | null
  price: number | null
  currency: string | null
  url: string
  source: string
  match_score: number
  review_sentiment: 'positive' | 'neutral' | 'negative' | 'unknown'
  sentiment_score: number | null
  fake_review_probability: number | null
  availability: string | null
  primary_image_url: string | null
  images: Image[]
  sentiment_reason: string | null
  sentiment_highlights: string[]
  product_type: string | null
  category_match: boolean | null
}

interface SearchResponse {
  query: string
  items: ProductItem[]
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  intent?: {
    query_text: string
    category: string | null
    brand: string | null
    model: string | null
    core_specs: string[]
  }
}

function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<SearchResponse | null>(null)

  const handleSearch = async () => {
    if (!input.trim() || loading) return

    const userMessage: Message = { role: 'user', content: input }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: input })
      })

      if (!response.ok) {
        throw new Error('Search failed')
      }

      const data: SearchResponse = await response.json()
      setResults(data)

      const assistantMessage: Message = {
        role: 'assistant',
        content: `Found ${data.items.length} matching products. Check the results panel →`,
        intent: {
          query_text: data.query,
          category: null,
          brand: null,
          model: null,
          core_specs: []
        }
      }
      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      const errorMessage: Message = {
        role: 'assistant',
        content: 'Sorry, there was an error processing your search. Please try again.'
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  const getSentimentIcon = (sentiment: string) => {
    if (sentiment === 'positive') return <TrendingUp className="w-4 h-4 text-green-600" />
    if (sentiment === 'negative') return <TrendingDown className="w-4 h-4 text-red-600" />
    return <Minus className="w-4 h-4 text-gray-600" />
  }

  const getSentimentColor = (sentiment: string) => {
    if (sentiment === 'positive') return 'text-green-600'
    if (sentiment === 'negative') return 'text-red-600'
    return 'text-gray-600'
  }

  return (
    <div className="flex h-screen bg-gray-50">
      <div className="w-1/2 flex flex-col border-r border-gray-200 bg-white">
        <div className="p-6 border-b border-gray-200 bg-blue-50">
          <h2 className="text-xl font-semibold text-gray-900">Conversation</h2>
          <p className="text-sm text-gray-600">Chat to refine your search</p>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.map((message, index) => (
            <div key={index} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {message.role === 'user' ? (
                <div className="bg-blue-500 text-white px-4 py-2 rounded-lg max-w-md">
                  {message.content}
                </div>
              ) : (
                <div className="bg-green-50 border border-green-200 px-4 py-3 rounded-lg max-w-md">
                  <p className="text-gray-900">{message.content}</p>
                  {message.intent && (
                    <div className="mt-2">
                      <p className="text-xs text-gray-600 mb-1">Search Intent:</p>
                      <div className="flex flex-wrap gap-1">
                        {message.intent.category && (
                          <Badge variant="secondary" className="bg-blue-100 text-blue-800">
                            {message.intent.category}
                          </Badge>
                        )}
                        {message.intent.brand && (
                          <Badge variant="secondary" className="bg-amber-100 text-amber-800">
                            {message.intent.brand}
                          </Badge>
                        )}
                        {message.intent.model && (
                          <Badge variant="secondary" className="bg-purple-100 text-purple-800">
                            {message.intent.model}
                          </Badge>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 px-4 py-2 rounded-lg">
                <p className="text-gray-600">Searching...</p>
              </div>
            </div>
          )}
        </div>

        <div className="p-4 border-t border-gray-200">
          <div className="flex gap-2">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Describe the item or refine your search..."
              className="flex-1"
              disabled={loading}
            />
            <Button onClick={handleSearch} disabled={loading || !input.trim()}>
              <Send className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>

      <div className="w-1/2 flex flex-col bg-green-50">
        <div className="p-6 border-b border-gray-200 bg-green-100">
          <h2 className="text-xl font-semibold text-gray-900">Product Results</h2>
          <p className="text-sm text-gray-600">
            {results ? `${results.items.length} products found` : 'No search yet'}
          </p>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {results?.items.map((item, index) => (
            <Card key={index} className="bg-white">
              <CardContent className="p-6">
                {item.primary_image_url && (
                  <div className="mb-4">
                    <img 
                      src={item.primary_image_url} 
                      alt={item.normalized_title || item.title}
                      className="w-full h-48 object-contain rounded-lg bg-gray-50"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = 'none'
                      }}
                    />
                  </div>
                )}
                
                {item.images.length > 1 && (
                  <div className="flex gap-2 mb-4 overflow-x-auto">
                    {item.images.slice(0, 4).map((img, imgIndex) => (
                      <img
                        key={imgIndex}
                        src={img.url}
                        alt={img.alt || `${item.normalized_title || item.title} thumbnail ${imgIndex + 1}`}
                        className="w-16 h-16 object-cover rounded border border-gray-200 flex-shrink-0"
                        onError={(e) => {
                          (e.target as HTMLImageElement).style.display = 'none'
                        }}
                      />
                    ))}
                  </div>
                )}

                <div className="flex justify-between items-start mb-3">
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900 mb-1">
                      {item.normalized_title || item.title}
                    </h3>
                    {item.normalized_title && item.normalized_title !== item.title && (
                      <p className="text-xs text-gray-500 mb-1">{item.title}</p>
                    )}
                    <p className="text-sm text-gray-600">{item.source}</p>
                  </div>
                  {item.availability && (
                    <Badge variant="outline" className={
                      item.availability.toLowerCase().includes('stock')
                        ? 'bg-green-50 text-green-700 border-green-200'
                        : 'bg-yellow-50 text-yellow-700 border-yellow-200'
                    }>
                      {item.availability.toLowerCase().includes('stock') ? 'In Stock' : item.availability}
                    </Badge>
                  )}
                </div>

                <div className="mb-4">
                  <p className="text-2xl font-bold text-gray-900">
                    {item.price !== null && item.currency ? `$${item.price.toFixed(2)} ${item.currency}` : 'Price not available'}
                  </p>
                </div>

                <div className="mb-3">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-sm text-gray-600">Match Score</span>
                    <span className="text-sm font-semibold">{Math.round(item.match_score * 100)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-gray-900 h-2 rounded-full"
                      style={{ width: `${item.match_score * 100}%` }}
                    />
                  </div>
                </div>

                {item.review_sentiment !== 'unknown' && (
                  <div className="mb-4">
                    <div className="flex items-center gap-2 mb-2">
                      {getSentimentIcon(item.review_sentiment)}
                      <span className={`text-sm font-medium ${getSentimentColor(item.review_sentiment)}`}>
                        Sentiment: {item.review_sentiment.charAt(0).toUpperCase() + item.review_sentiment.slice(1)}
                        {item.sentiment_score !== null && ` (${Math.round(item.sentiment_score * 100)}%)`}
                      </span>
                    </div>
                    {item.sentiment_reason && (
                      <p className="text-xs text-gray-600 mb-2 italic">{item.sentiment_reason}</p>
                    )}
                    {item.sentiment_highlights && item.sentiment_highlights.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {item.sentiment_highlights.slice(0, 5).map((highlight, idx) => (
                          <Badge key={idx} variant="secondary" className="text-xs bg-gray-100 text-gray-700">
                            {highlight}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                <Button
                  variant="outline"
                  className="w-full"
                  onClick={() => window.open(item.url, '_blank')}
                >
                  View Product
                  <ExternalLink className="w-4 h-4 ml-2" />
                </Button>
              </CardContent>
            </Card>
          ))}

          {!results && (
            <div className="flex items-center justify-center h-full">
              <p className="text-gray-500 text-center">
                Start a search to see product results
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default App
