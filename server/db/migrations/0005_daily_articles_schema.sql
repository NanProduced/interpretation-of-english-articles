CREATE TABLE daily_articles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_provider TEXT NOT NULL CHECK (source_provider IN ('spaceflight_news', 'newsapi', 'wikipedia', 'other')),
  source_id TEXT NOT NULL,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  content_word_count INTEGER NOT NULL,
  source_url TEXT NOT NULL,
  image_url TEXT,
  publish_date DATE,
  fetch_date DATE NOT NULL DEFAULT CURRENT_DATE,
  language TEXT NOT NULL DEFAULT 'en',
  category TEXT,
  tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  source_metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived', 'hidden')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_daily_articles_source UNIQUE (source_provider, source_id)
);

CREATE INDEX idx_daily_articles_fetch_date ON daily_articles(fetch_date DESC);
CREATE INDEX idx_daily_articles_status ON daily_articles(status);
CREATE INDEX idx_daily_articles_publish_date ON daily_articles(publish_date DESC);
CREATE INDEX idx_daily_articles_word_count ON daily_articles(content_word_count);

CREATE TABLE daily_article_fetch_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  fetch_date DATE NOT NULL DEFAULT CURRENT_DATE,
  source_provider TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('success', 'partial', 'failed')),
  articles_fetched INTEGER NOT NULL DEFAULT 0,
  articles_valid INTEGER NOT NULL DEFAULT 0,
  articles_saved INTEGER NOT NULL DEFAULT 0,
  error_message TEXT,
  duration_ms INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_daily_article_fetch_logs_fetch_date ON daily_article_fetch_logs(fetch_date DESC);
CREATE INDEX idx_daily_article_fetch_logs_status ON daily_article_fetch_logs(status);

COMMENT ON TABLE daily_articles IS '每日精读文章表，存储从外部数据源抓取并清洗后的英文文章。';
COMMENT ON COLUMN daily_articles.id IS '文章主键，UUID。';
COMMENT ON COLUMN daily_articles.source_provider IS '数据源提供商：spaceflight_news, newsapi, wikipedia, other。';
COMMENT ON COLUMN daily_articles.source_id IS '原始数据源中的文章唯一标识。';
COMMENT ON COLUMN daily_articles.title IS '文章标题。';
COMMENT ON COLUMN daily_articles.content IS '清洗后的正文内容。';
COMMENT ON COLUMN daily_articles.content_word_count IS '正文词数，用于筛选500-1200词的文章。';
COMMENT ON COLUMN daily_articles.source_url IS '原始文章URL。';
COMMENT ON COLUMN daily_articles.image_url IS '文章封面图片URL（可选）。';
COMMENT ON COLUMN daily_articles.publish_date IS '文章原始发布日期。';
COMMENT ON COLUMN daily_articles.fetch_date IS '抓取日期，用于每日分组。';
COMMENT ON COLUMN daily_articles.language IS '文章语言，固定为 en。';
COMMENT ON COLUMN daily_articles.category IS '文章分类（可选）。';
COMMENT ON COLUMN daily_articles.tags IS '文章标签数组。';
COMMENT ON COLUMN daily_articles.source_metadata_json IS '原始数据源的元数据JSON。';
COMMENT ON COLUMN daily_articles.status IS '文章状态：active, archived, hidden。';

COMMENT ON TABLE daily_article_fetch_logs IS '每日文章抓取日志表，记录每次抓取任务的执行情况。';
COMMENT ON COLUMN daily_article_fetch_logs.id IS '日志主键，UUID。';
COMMENT ON COLUMN daily_article_fetch_logs.fetch_date IS '抓取日期。';
COMMENT ON COLUMN daily_article_fetch_logs.source_provider IS '数据源提供商。';
COMMENT ON COLUMN daily_article_fetch_logs.status IS '抓取状态：success, partial, failed。';
COMMENT ON COLUMN daily_article_fetch_logs.articles_fetched IS '从数据源获取的原始文章数。';
COMMENT ON COLUMN daily_article_fetch_logs.articles_valid IS '通过词数和语言验证的文章数。';
COMMENT ON COLUMN daily_article_fetch_logs.articles_saved IS '实际保存到数据库的文章数（去重后）。';
COMMENT ON COLUMN daily_article_fetch_logs.error_message IS '错误信息（如果抓取失败）。';
COMMENT ON COLUMN daily_article_fetch_logs.duration_ms IS '抓取任务执行耗时（毫秒）。';

CREATE TRIGGER trg_daily_articles_set_updated_at
BEFORE UPDATE ON daily_articles
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
