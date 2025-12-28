# AI Implementation Guide for Habit Tracker

## 📋 Overview

This guide covers implementing AI features in your habit tracking application using **free, cloud-based AI services** that work with Vercel serverless functions and Supabase database.

---

## 🎯 AI Use Cases for Habit Tracker

### 1. **Enhanced Insights & Recommendations**
- Personalized habit recommendations based on user patterns
- Smart habit pairing suggestions (e.g., "People who track meditation also track journaling")
- Time-based recommendations (best times to do habits)
- Failure pattern analysis and recovery suggestions

### 2. **Motivational Content**
- Dynamic motivational messages based on progress
- Personalized encouragement during streaks
- Recovery messages after missed days
- Celebration messages for milestones

### 3. **Predictive Analytics**
- Predict which habits user might miss
- Suggest optimal habit timing
- Forecast completion rates
- Identify at-risk habits

### 4. **Smart Notifications**
- AI-generated reminder messages
- Context-aware notifications
- Personalized notification timing suggestions

### 5. **Habit Discovery**
- Suggest new habits based on existing ones
- Category-based recommendations
- Goal-oriented habit suggestions

---

## 🆓 Free AI API Options (No Local Models)

### Option 1: **Hugging Face Inference API** ⭐ RECOMMENDED
**Best for: Free tier with good limits**

- **Free Tier:** 1,000 requests/month free
- **Models Available:** 
  - `mistralai/Mistral-7B-Instruct-v0.2` (Free, fast)
  - `meta-llama/Llama-2-7b-chat-hf` (Free)
  - `google/flan-t5-large` (Free, lightweight)
- **Speed:** Fast (usually <2s)
- **Rate Limits:** 1,000 requests/month, then pay-as-you-go
- **Setup:** Simple API key, REST API
- **Best For:** General insights, recommendations, text generation

**Pros:**
- ✅ Truly free tier
- ✅ Multiple model options
- ✅ Fast inference
- ✅ Good for serverless (low latency)

**Cons:**
- ⚠️ Limited free requests (1K/month)
- ⚠️ May need multiple accounts for scale

---

### Option 2: **Google Gemini API** ⭐ BEST FREE TIER
**Best for: Highest free limits**

- **Free Tier:** 15 requests per minute (RPM), 1,500 requests per day (RPD)
- **Model:** `gemini-pro` (Free)
- **Speed:** Very fast (<1s)
- **Rate Limits:** 15 RPM, 1,500 RPD (free tier)
- **Setup:** API key from Google AI Studio
- **Best For:** All use cases, best free tier limits

**Pros:**
- ✅ Best free tier (1,500 requests/day = ~45K/month)
- ✅ Very fast
- ✅ High quality responses
- ✅ Good for production

**Cons:**
- ⚠️ Rate limits (15/min) - need caching/queuing
- ⚠️ Requires Google account

---

### Option 3: **Groq API** ⭐⭐ BEST FOR SCALABILITY (RECOMMENDED)
**Best for: Speed, scalability, and unlimited tokens**

- **Free Tier:** 
  - `groq/compound` & `groq/compound-mini`: 30 RPM, 250 RPD, 70K TPM, **UNLIMITED TPD** 🚀
  - `llama-3.1-8b-instant`: 30 RPM, 14.4K RPD, 6K TPM, 500K TPD
  - `llama-3.3-70b-versatile`: 30 RPM, 1K RPD, 12K TPM, 100K TPD
- **Models:** Multiple high-quality models (Llama, Mixtral, etc.)
- **Speed:** Extremely fast (<500ms, often <200ms)
- **Rate Limits:** See above (unlimited tokens/day for compound models!)
- **Setup:** API key, REST API
- **Best For:** Production apps with many users, real-time insights, scalable systems

**Pros:**
- ✅ **UNLIMITED tokens per day** for compound models (perfect for scaling!)
- ✅ Fastest inference speed (<500ms)
- ✅ High-quality models
- ✅ Excellent for serverless (low latency)
- ✅ Can batch multiple insights in one request
- ✅ Free tier is very generous

**Cons:**
- ⚠️ 250 requests/day for compound (but unlimited tokens = can batch)
- ⚠️ Need to batch requests efficiently

---

### Option 4: **Together AI**
**Best for: Open-source models**

- **Free Tier:** Limited free tier
- **Models:** Various open-source models
- **Speed:** Fast
- **Best For:** Open-source model access

---

### Option 5: **OpenAI API** (Not Recommended for Free)
- **Free Tier:** Very limited ($5 credit, expires)
- **Cost:** $0.002 per 1K tokens (expensive at scale)
- **Best For:** Only if you have budget

---

## 🏗️ Architecture for Vercel + Supabase

### Serverless Architecture

```
User Request → Vercel Serverless Function → AI API → Response
                     ↓
              Supabase (Cache Results)
```

### Key Considerations:

1. **Cold Starts:** Vercel functions have ~100-500ms cold start
   - **Solution:** Keep functions warm with scheduled pings
   - **Solution:** Cache AI responses in Supabase

2. **Rate Limiting:** Free AI APIs have rate limits
   - **Solution:** Implement request queuing
   - **Solution:** Cache responses for 24 hours
   - **Solution:** Batch requests when possible

3. **Cost Management:**
   - **Solution:** Cache all AI responses
   - **Solution:** Only call AI for new/updated data
   - **Solution:** Use lightweight prompts

4. **Scalability:**
   - **Solution:** Store AI insights in Supabase
   - **Solution:** Background job to refresh insights
   - **Solution:** User-specific caching

---

## 💾 Database Schema (Supabase)

### New Tables Needed:

```sql
-- AI-generated insights cache
CREATE TABLE ai_insights (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES "user"(id) ON DELETE CASCADE,
    insight_type VARCHAR(50), -- 'recommendation', 'motivation', 'prediction'
    content TEXT,
    metadata JSONB, -- Store habit IDs, dates, etc.
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP, -- Cache expiration
    model_used VARCHAR(50), -- Track which AI model
    INDEX idx_user_expires (user_id, expires_at)
);

-- AI request logs (for monitoring)
CREATE TABLE ai_request_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES "user"(id),
    endpoint VARCHAR(100),
    model_used VARCHAR(50),
    tokens_used INTEGER,
    response_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 🔧 Implementation Strategy

### Phase 1: Basic AI Insights (Week 1)
**Goal:** Replace current rule-based insights with AI-generated ones

1. **Setup AI Service**
   - Choose: **Groq API** (unlimited tokens, fastest)
   - Model: `groq/compound-mini` (unlimited tokens/day)
   - Create API wrapper service
   - Implement caching layer
   - Implement batching for multiple users

2. **Enhance `/api/insights` endpoint**
   - Check cache first
   - If cache miss, call AI API
   - Store results in Supabase
   - Return personalized insights

3. **Prompt Engineering**
   - Create effective prompts for habit insights
   - Include user data (habits, progress, streaks)
   - Generate 3-5 insights per request

### Phase 2: Smart Recommendations (Week 2)
**Goal:** AI-powered habit recommendations

1. **New Endpoint:** `/api/ai/recommendations`
   - Analyze user's habits
   - Suggest new habits
   - Suggest habit pairings
   - Time-based recommendations

2. **Features:**
   - "People also track" suggestions
   - Category-based recommendations
   - Goal-oriented suggestions

### Phase 3: Predictive Analytics (Week 3)
**Goal:** Predict and prevent habit failures

1. **New Endpoint:** `/api/ai/predictions`
   - Predict which habits might be missed
   - Identify at-risk streaks
   - Suggest intervention strategies

2. **Features:**
   - Daily risk assessment
   - Proactive notifications
   - Recovery suggestions

### Phase 4: Advanced Features (Week 4+)
**Goal:** Advanced AI features

1. **Smart Notifications**
   - AI-generated reminder messages
   - Personalized timing suggestions

2. **Habit Discovery**
   - AI-powered habit search
   - Context-aware suggestions

---

## 📝 Example Implementation

### 1. AI Service Wrapper (`services/ai_service.py`)

```python
import os
import requests
from datetime import datetime, timedelta
import json

class AIService:
    def __init__(self):
        self.api_key = os.environ.get('GEMINI_API_KEY')
        self.base_url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent'
        self.cache_duration = timedelta(hours=24)
    
    def generate_insights(self, user_data):
        """
        Generate personalized insights for user
        
        user_data: {
            'habits': [...],
            'stats': {...},
            'streaks': [...],
            'recent_activity': [...]
        }
        """
        prompt = self._build_insights_prompt(user_data)
        
        response = requests.post(
            self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a helpful habit tracking assistant. Generate personalized, motivational insights."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 1000
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            insights_text = result['choices'][0]['message']['content']
            return self._parse_insights(insights_text)
        else:
            # Fallback to rule-based insights
            return self._fallback_insights(user_data)
    
    def _build_insights_prompt(self, user_data):
        habits_text = "\n".join([
            f"- {h['emoji']} {h['name']}: {h['completed']}/{h['goal']} ({h['percentage']:.1f}%)"
            for h in user_data['habits']
        ])
        
        return f"""You are a helpful habit tracking assistant. Generate 3-5 personalized, motivational insights for this user.

User's Habits:
{habits_text}

Overall Progress: {user_data['stats']['overall_pct']:.1f}%
Today's Completions: {user_data['stats']['today_completions']}
Current Streaks: {user_data['stats']['max_streak']} days

Generate insights that:
1. Celebrate achievements first
2. Provide specific, actionable recommendations
3. Are motivational and encouraging
4. Reference specific habits by name

Format as JSON array:
[
  {{"type": "success|info|warning", "icon": "🔥", "message": "..."}},
  ...
]
"""
    
    def _parse_insights(self, text):
        # Parse AI response and extract insights
        # Handle JSON extraction
        pass
    
    def _fallback_insights(self, user_data):
        # Return rule-based insights if AI fails
        pass
```

### 2. Caching Layer

```python
def get_cached_insights(user_id):
    """Check Supabase for cached insights"""
    # Query ai_insights table
    # Return if not expired
    pass

def cache_insights(user_id, insights):
    """Store insights in Supabase"""
    # Insert into ai_insights table
    # Set expiration to 24 hours
    pass
```

### 3. Updated `/api/insights` Endpoint

```python
@app.route('/api/insights', methods=['GET'])
@api_login_required
def get_insights():
    user_id = current_user.id
    
    # Check cache first
    cached = get_cached_insights(user_id)
    if cached and cached['expires_at'] > datetime.utcnow():
        return jsonify({'insights': cached['content']})
    
    # Gather user data
    user_data = gather_user_habit_data(user_id)
    
    # Generate AI insights
    ai_service = AIService()
    insights = ai_service.generate_insights(user_data)
    
    # Cache results
    cache_insights(user_id, insights)
    
    return jsonify({'insights': insights})
```

---

## 🚀 Performance Optimization

### 1. **Caching Strategy**
- Cache AI responses for 24 hours
- Invalidate cache when user completes habits
- Use Supabase for distributed caching

### 2. **Request Batching** (Critical for Groq's 250 requests/day)
- **Batch Strategy:** Group multiple users in single AI request
- **Example:** 1 request can generate insights for 10 users (unlimited tokens!)
- **Implementation:** 
  - Queue user requests
  - Batch every 5-10 users or every 5 minutes
  - Single API call generates insights for entire batch
  - Distribute results to individual users
- **Result:** 250 requests/day × 10 users/batch = 2,500+ users served!
- **Process in background jobs**
- **Update cache asynchronously**

### 3. **Fallback System**
- Always have rule-based fallback
- Graceful degradation if AI fails
- Monitor AI API health

### 4. **Rate Limit Management**
- Implement request queue
- Prioritize active users
- Use multiple API keys if needed

---

## 💰 Cost Estimation (Free Tier)

### Groq (Recommended):
- **Free:** 
  - `groq/compound`: 250 requests/day, **UNLIMITED tokens/day** 🚀
  - `llama-3.1-8b-instant`: 14,400 requests/day, 500K tokens/day
- **Cost after free tier:** Check current pricing
- **Estimated:** $0/month for 100+ active users (with proper caching and batching)
- **Scalability:** Unlimited tokens = can handle massive scale with batching

### Google Gemini:
- **Free:** 1,500 requests/day = 45,000/month
- **Cost after free tier:** $0.00025 per 1K characters
- **Estimated:** $0-5/month for 100 active users

### Hugging Face:
- **Free:** 1,000 requests/month
- **Cost after:** ~$0.001 per request
- **Estimated:** $0-10/month for 100 active users

---

## 🔒 Security & Privacy

1. **API Key Management**
   - Store in Vercel environment variables
   - Never expose in frontend
   - Rotate keys regularly

2. **Data Privacy**
   - Don't send PII to AI APIs
   - Anonymize user data
   - Cache responses securely

3. **Rate Limiting**
   - Implement per-user rate limits
   - Prevent abuse
   - Monitor usage

---

## 📊 Monitoring & Analytics

### Track:
- AI API response times
- Cache hit rates
- Error rates
- Cost per user
- User engagement with AI insights

### Tools:
- Vercel Analytics
- Supabase Logs
- Custom logging in `ai_request_logs` table

---

## 🎯 Recommended Approach

### **Start with Groq API** ⭐ TOP CHOICE

**Why Groq is Best for Your Use Case:**
1. ✅ **UNLIMITED tokens per day** for compound models (perfect for scaling!)
2. ✅ **Fastest responses** (<500ms, often <200ms)
3. ✅ **High quality models** (Llama, Mixtral)
4. ✅ **Perfect for serverless** (low latency, fast cold starts)
5. ✅ **Can batch requests** (250 requests/day = can serve many users with batching)
6. ✅ **Free tier** is very generous
7. ✅ **Production-ready** and reliable

**Strategy:**
- Use `groq/compound` or `groq/compound-mini` for unlimited tokens
- Batch multiple user insights in single requests
- Cache aggressively (24 hours)
- 250 requests/day = can serve 250+ users with proper caching

### **Alternative: Google Gemini API** (If you need more requests/day)

**Why:**
1. ✅ 1,500 requests/day (better for high request volume)
2. ✅ Fast responses (<1s)
3. ✅ High quality
4. ✅ Easy integration

**Implementation Order:**
1. Week 1: Replace `/api/insights` with AI
2. Week 2: Add `/api/ai/recommendations`
3. Week 3: Add predictive analytics
4. Week 4+: Advanced features

**Fallback Strategy:**
- Always keep rule-based insights as fallback
- Cache aggressively
- Monitor costs and usage

---

## 📚 Next Steps

1. **Choose AI Provider:** Groq API (recommended - unlimited tokens!)
2. **Setup API Key:** Get from https://console.groq.com/
3. **Choose Model:** `groq/compound` or `groq/compound-mini` for unlimited tokens
4. **Create Database Tables:** Add to Supabase
5. **Implement Caching:** Use Supabase for cache (24 hours)
6. **Build AI Service:** Create wrapper service with batching support
7. **Update Endpoints:** Integrate AI into existing endpoints
8. **Test & Monitor:** Test with real users, monitor performance

---

## 🔗 Resources

- **Groq API:** https://console.groq.com/ (Get API key here)
- **Groq Documentation:** https://console.groq.com/docs
- **Groq Models:** https://console.groq.com/docs/models
- **Google Gemini:** https://ai.google.dev/ (Alternative)
- **Hugging Face:** https://huggingface.co/inference-api (Alternative)
- **Vercel Serverless:** https://vercel.com/docs/functions
- **Supabase:** https://supabase.com/docs

---

## ❓ Questions to Consider

1. **Which AI provider?** → **Groq API** (unlimited tokens, fastest, best for scale)
2. **Which model?** → `groq/compound` or `groq/compound-mini` (unlimited tokens/day)
3. **How to handle 250 requests/day limit?** → Batch multiple users in one request, cache aggressively
4. **How to cache?** → Supabase table with 24-hour expiration
5. **When to refresh?** → On habit completion, daily background job
6. **How to scale?** → Batching + caching + unlimited tokens = can serve thousands of users
7. **What if AI fails?** → Fallback to rule-based insights

---

**Ready to implement?** Let me know and we'll start with Phase 1!

