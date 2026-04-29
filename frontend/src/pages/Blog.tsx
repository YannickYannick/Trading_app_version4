import { Link } from 'react-router-dom'
import './Blog.css'

type BlogItem = {
  slug: string
  title: string
  excerpt: string
  tags: string[]
}

const BLOG_ITEMS: BlogItem[] = [
  {
    slug: 'flux-petrole',
    title: "Chaîne d'approvisionnement pétrolière mondiale",
    excerpt:
      "Carte interactive + analyse (Brent/WTI, ratios, raffinage) pour visualiser les flux et mieux comprendre l'industrie.",
    tags: ['pétrole', 'macro', 'supply chain', 'amCharts'],
  },
]

export default function Blog() {
  return (
    <div className="blog-page">
      <div className="blog-header">
        <h1>Blog</h1>
        <p>Articles et visualisations.</p>
      </div>

      <div className="blog-grid">
        {BLOG_ITEMS.map((item) => (
          <Link key={item.slug} to={`/blog/${item.slug}`} className="blog-card">
            <div className="blog-card-title">{item.title}</div>
            <div className="blog-card-excerpt">{item.excerpt}</div>
            <div className="blog-card-tags">
              {item.tags.map((t) => (
                <span key={t} className="blog-tag">
                  {t}
                </span>
              ))}
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}

