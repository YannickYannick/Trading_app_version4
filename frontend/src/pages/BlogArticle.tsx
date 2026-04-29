import { Link, Navigate, useParams } from 'react-router-dom'
import './BlogArticle.css'

const ARTICLE_MAP: Record<string, { title: string; htmlPath: string }> = {
  'flux-petrole': {
    title: "Chaîne d'approvisionnement pétrolière mondiale",
    htmlPath: '/blog/flux-petrole.html',
  },
}

export default function BlogArticle() {
  const { slug } = useParams()

  if (!slug) return <Navigate to="/blog" replace />

  const article = ARTICLE_MAP[slug]
  if (!article) return <Navigate to="/blog" replace />

  return (
    <div className="blog-article-page">
      <div className="blog-article-topbar">
        <Link className="blog-article-back" to="/blog">
          ← Retour au blog
        </Link>
        <div className="blog-article-title">{article.title}</div>
      </div>

      <iframe
        className="blog-article-frame"
        src={article.htmlPath}
        title={article.title}
        loading="lazy"
        referrerPolicy="no-referrer"
      />
    </div>
  )
}

