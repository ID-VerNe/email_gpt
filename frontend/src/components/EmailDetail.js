import React, { useState, useEffect, useMemo, useRef } from 'react';
import { marked } from 'marked';
import './EmailDetail.css';
import { highlightText } from '../utils/highlightText';

const ImageModal = ({ src, onClose }) => {
    if (!src) return null;
    return (
        <div className="image-modal-backdrop" onClick={onClose}>
            <div className="image-modal-content" onClick={e => e.stopPropagation()}>
                <span className="image-modal-close" onClick={onClose}>&times;</span>
                <img src={src} alt="全屏邮件图片" />
            </div>
        </div>
    );
};

const EmailBody = ({ raw_email_body, highlightTerm }) => {
    const [modalImageSrc, setModalImageSrc] = useState(null);
    const contentRef = useRef(null);
    const containerRef = useRef(null);

    const highlightedBody = useMemo(() => {
        if (!highlightTerm) return raw_email_body;
        return raw_email_body;
    }, [raw_email_body, highlightTerm]);

    useEffect(() => {
        const handleImageClick = (event) => {
            if (event.target.tagName === 'IMG') {
                setModalImageSrc(event.target.src);
            }
        };

        const contentDiv = contentRef.current;
        if (contentDiv) {
            contentDiv.addEventListener('click', handleImageClick);
        }

        return () => {
            if (contentDiv) {
                contentDiv.removeEventListener('click', handleImageClick);
            }
        };
    }, [highlightedBody]);

    useEffect(() => {
        if (containerRef.current) {
            containerRef.current.scrollTop = 0;
        }
    }, [highlightedBody]);

    return (
        <>
            <div ref={containerRef} className="email-body-container">
                <h3>原文</h3>
                <div ref={contentRef} className="email-body-content" dangerouslySetInnerHTML={{ __html: highlightedBody }} />
            </div>
            <ImageModal src={modalImageSrc} onClose={() => setModalImageSrc(null)} />
        </>
    );
};

const EmailAnalysis = ({ analysis_markdown, highlightTerm }) => {
    const containerRef = useRef(null);

    useEffect(() => {
        if (containerRef.current) {
            containerRef.current.scrollTop = 0;
        }
    }, [analysis_markdown]);

    marked.setOptions({
        breaks: true,
    });

    const getMarkdownText = () => {
        const rawMarkup = marked(analysis_markdown || '');
        if (!highlightTerm) return { __html: rawMarkup };

        const escapedHighlight = highlightTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(`(${escapedHighlight})`, 'gi');
        const highlightedMarkup = rawMarkup.replace(regex, '<mark>$1</mark>');
        
        return { __html: highlightedMarkup };
    };

    return (
        <div ref={containerRef} className="email-analysis-container">
            <h3>分析结果</h3>
            <div className="email-analysis-content" dangerouslySetInnerHTML={getMarkdownText()} />
        </div>
    );
};

const EmailActions = ({ email, onUpdateEmail, onUpdateUrgency }) => {
    const handleStarToggle = () => {
        onUpdateEmail(email.id, { is_starred: !email.is_starred });
    };

    const handleReadToggle = () => {
        onUpdateEmail(email.id, { is_read: !email.is_read });
    };

    const urgencyBlock = email.analysis_json?.['邮件紧急程度评估'] || email.analysis_json?.['郵件緊急程度評估'];
    const currentUrgency = urgencyBlock?.[0]?.['- **紧急程度**'] || urgencyBlock?.[0]?.['- **緊急程度**'] || '未评估';

    const handleUrgencyCycle = () => {
        const urgencyLevels = ['低', '中', '高'];
        const currentIndex = urgencyLevels.indexOf(currentUrgency);
        const nextIndex = (currentIndex + 1) % urgencyLevels.length;
        const newUrgency = urgencyLevels[nextIndex];
        onUpdateUrgency(email.id, newUrgency);
    };

    const getUrgencyEmoji = () => {
        switch (currentUrgency) {
            case '高':
                return '🔥';
            case '中':
                return '⚠️';
            case '低':
                return '🟢';
            default:
                return '⚪';
        }
    };

    return (
        <div className="email-actions-floating">
            <button 
                onClick={handleStarToggle} 
                className={`action-button ${email.is_starred ? 'starred' : ''}`}
                title={email.is_starred ? '取消星标' : '星标'}
            >
                {email.is_starred ? '★' : '☆'}
            </button>
            <button 
                onClick={handleReadToggle} 
                className={`action-button ${email.is_read ? 'read' : ''}`}
                title={email.is_read ? '标记为未读' : '标记为已读'}
            >
                {email.is_read ? '✓' : '✉'}
            </button>
            <button 
                onClick={handleUrgencyCycle} 
                className="action-button urgency-button"
                title={`循环紧急程度 (当前: ${currentUrgency})`}
            >
                {getUrgencyEmoji()}
            </button>
        </div>
    );
};

const EmailDetail = ({ email, onUpdateEmail, onUpdateUrgency, searchQuery }) => {
    if (!email) {
        return <div className="email-detail-placeholder">请在左侧选择一封邮件查看详情</div>;
    }
    
    const getHighlightTerm = () => {
        if (!searchQuery) return '';
        const parts = searchQuery.split(':');
        return parts.length > 1 ? parts.slice(1).join(':') : parts[0];
    };
    const highlightTerm = getHighlightTerm();

    return (
        <div className="email-detail-view">
            <EmailBody raw_email_body={email.raw_email_body} highlightTerm={highlightTerm} />
            <EmailAnalysis analysis_markdown={email.analysis_markdown} highlightTerm={highlightTerm} />
            <EmailActions email={email} onUpdateEmail={onUpdateEmail} onUpdateUrgency={onUpdateUrgency} />
        </div>
    );
};

export default EmailDetail;
