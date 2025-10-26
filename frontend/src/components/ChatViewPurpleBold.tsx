import { useState } from 'react';
import { Card } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import { ScrollArea } from './ui/scroll-area';
import { Send, ShieldAlert, TrendingUp, TrendingDown, Minus, ExternalLink } from 'lucide-react';

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
  price_min: number | null
  price_max: number | null
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
  is_listing_page: boolean | null
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

export function ChatViewPurpleBold() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SearchResponse | null>(null);

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

  const formatPrice = (item: ProductItem) => {
    if (item.price_min !== null && item.price_max !== null) {
      if (item.price_min === item.price_max) {
        return `$${item.price_min.toFixed(2)} ${item.currency || 'USD'}`
      }
      return `$${item.price_min.toFixed(2)} - $${item.price_max.toFixed(2)} ${item.currency || 'USD'}`
    }
    if (item.price_min !== null) {
      return `From $${item.price_min.toFixed(2)} ${item.currency || 'USD'}`
    }
    if (item.price_max !== null) {
      return `Up to $${item.price_max.toFixed(2)} ${item.currency || 'USD'}`
    }
    if (item.price !== null && item.currency) {
      return `$${item.price.toFixed(2)} ${item.currency}`
    }
    if (item.is_listing_page) {
      return 'See site for current prices'
    }
    return 'Price not available'
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[calc(100vh-220px)]">
      {/* Chat Panel */}
      <Card className="flex flex-col bg-white/90 backdrop-blur-sm shadow-lg border-purple-200">
        <div className="border-b border-purple-100 px-4 py-3 bg-gradient-to-r from-purple-50 to-indigo-100">
          <h2 className="text-gray-900">Conversation</h2>
          <p className="text-sm text-gray-600">Chat to refine your search</p>
        </div>

        <ScrollArea className="flex-1 p-4">
          <div className="space-y-4">
            {messages.map((msg, idx) => (
              <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] rounded-lg px-4 py-2 ${
                  msg.role === 'user' 
                    ? 'bg-gradient-to-br from-purple-500 to-indigo-600 text-white shadow-md' 
                    : 'bg-gradient-to-br from-violet-50 to-purple-100 text-gray-900 border border-purple-200'
                }`}>
                  <p>{msg.content}</p>
                  {msg.intent && (
                    <div className="mt-2 pt-2 border-t border-purple-200 space-y-1">
                      <p className="text-sm opacity-90">Search Intent:</p>
                      <div className="flex flex-wrap gap-1">
                        {msg.intent.category && (
                          <Badge className="text-xs bg-purple-100 text-purple-700 hover:bg-purple-200">
                            {msg.intent.category}
                          </Badge>
                        )}
                        {msg.intent.brand && (
                          <Badge className="text-xs bg-indigo-100 text-indigo-700 hover:bg-indigo-200">
                            {msg.intent.brand}
                          </Badge>
                        )}
                        {msg.intent.model && (
                          <Badge className="text-xs bg-violet-100 text-violet-700 hover:bg-violet-200">
                            {msg.intent.model}
                          </Badge>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
            
            {loading && (
              <div className="flex justify-start">
                <div className="bg-gradient-to-br from-violet-50 to-purple-100 text-gray-900 rounded-lg px-4 py-2 border border-purple-200">
                  <p>Searching...</p>
                </div>
              </div>
            )}
          </div>
        </ScrollArea>

        <div className="border-t border-purple-100 p-4 bg-purple-50/50">
          <div className="flex gap-2">
            <Input 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Describe the item or refine your search..."
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              className="bg-white border-purple-200 focus:border-purple-300"
              disabled={loading}
            />
            <Button onClick={handleSearch} disabled={loading || !input.trim()} className="bg-gradient-to-br from-purple-500 to-indigo-600 hover:from-purple-600 hover:to-indigo-700">
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </Card>

      {/* Results Panel */}
      <Card className="flex flex-col bg-white/90 backdrop-blur-sm shadow-lg border-indigo-200">
        <div className="border-b border-indigo-100 px-4 py-3 bg-gradient-to-r from-indigo-50 to-purple-100">
          <h2 className="text-gray-900">Product Results</h2>
          <p className="text-sm text-gray-600">
            {results ? `${results.items.length} products found` : 'No search yet'}
          </p>
        </div>

        <ScrollArea className="flex-1 p-4">
          <div className="space-y-4">
            {results?.items.map((product, idx) => (
              <Card key={idx} className="p-4 hover:shadow-xl transition-all bg-gradient-to-br from-white to-purple-50 border-purple-100 hover:scale-[1.02]">
                <div className="flex justify-between items-start mb-3">
                  <div className="flex-1">
                    <h3 className="text-gray-900 mb-1">{product.normalized_title || product.title}</h3>
                    <p className="text-sm text-gray-600">{product.source}</p>
                  </div>
                  {product.availability && (
                    <Badge className={product.availability.toLowerCase().includes('stock') ? "bg-violet-100 text-violet-700 hover:bg-violet-200" : "bg-pink-100 text-pink-700 hover:bg-pink-200"}>
                      {product.availability}
                    </Badge>
                  )}
                </div>

                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-gray-900">{formatPrice(product)}</p>
                      {product.is_listing_page && (
                        <p className="text-xs text-gray-500 mt-1">Category page - price range</p>
                      )}
                    </div>
                    <Button variant="outline" size="sm" onClick={() => window.open(product.url, '_blank')}>
                      View Product <ExternalLink className="h-3 w-3 ml-1" />
                    </Button>
                  </div>

                  <div>
                    <div className="flex items-center justify-between text-sm mb-1">
                      <span className="text-gray-600">Match Score</span>
                      <span className="text-gray-900">{(product.match_score * 100).toFixed(0)}%</span>
                    </div>
                    <Progress value={product.match_score * 100} className="h-2" />
                  </div>

                  {product.review_sentiment !== 'unknown' && (
                    <div className="flex items-center justify-between pt-2 border-t">
                      <div className="flex items-center gap-2">
                        {product.review_sentiment === 'positive' && <TrendingUp className="h-4 w-4 text-green-600" />}
                        {product.review_sentiment === 'neutral' && <Minus className="h-4 w-4 text-gray-600" />}
                        {product.review_sentiment === 'negative' && <TrendingDown className="h-4 w-4 text-red-600" />}
                        <span className="text-sm text-gray-600">
                          Sentiment: <span className="capitalize">{product.review_sentiment}</span> {product.sentiment_score !== null && `(${(product.sentiment_score * 100).toFixed(0)}%)`}
                        </span>
                      </div>
                      
                      {product.fake_review_probability !== null && product.fake_review_probability > 0.3 && (
                        <div className="flex items-center gap-1 text-amber-600">
                          <ShieldAlert className="h-4 w-4" />
                          <span className="text-xs">{(product.fake_review_probability * 100).toFixed(0)}% fake</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
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
        </ScrollArea>
      </Card>
    </div>
  );
}
