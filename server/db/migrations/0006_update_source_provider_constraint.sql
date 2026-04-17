ALTER TABLE daily_articles
DROP CONSTRAINT IF EXISTS daily_articles_source_provider_check;

ALTER TABLE daily_articles
ADD CONSTRAINT daily_articles_source_provider_check
CHECK (source_provider IN ('spaceflight_news', 'newsapi', 'wikipedia', 'other', 'combined'));

COMMENT ON COLUMN daily_articles.source_provider IS '数据源提供商：spaceflight_news, newsapi, wikipedia, other, combined。';
