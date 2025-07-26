import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { marked } from 'marked';
import './App.css';
import SettingsPage from './SettingsPage'; // 引入设置页面组件

// 将子组件拆分到单独的文件中以保持整洁
const Sidebar = ({ groupedEmails, onSelectEmail, onFilterChange, urgencyFilter, onSync, onShowSettings }) => {
    const [expanded, setExpanded] = useState(() => {
        // 默认展开所有年份
        const initialExpanded = {};
        Object.keys(groupedEmails).forEach(year => {
            initialExpanded[year] = true;
        });
        return initialExpanded;
    });

    const toggleExpand = (key) => {
        setExpanded(prev => ({ ...prev, [key]: !prev[key] }));
    };

    const toggleAllChildren = (e, childrenKeys) => {
        e.stopPropagation();
        const areAnyExpanded = childrenKeys.some(key => expanded[key]);
        const newExpandedState = {};
        childrenKeys.forEach(key => {
            newExpandedState[key] = !areAnyExpanded;
        });
        setExpanded(prev => ({ ...prev, ...newExpandedState }));
    };

    const getUrgencyClass = (email) => {
        const urgencyBlock = email.analysis_json?.['邮件紧急程度评估'] || email.analysis_json?.['郵件緊急程度評估'];
        const urgency = urgencyBlock?.[0]?.['- **紧急程度**'] || urgencyBlock?.[0]?.['- **緊急程度**'];
        switch (urgency) {
            case '高': return 'urgency-high';
            case '中': return 'urgency-medium';
            case '低': return 'urgency-low';
            default: return '';
        }
    };

    const sortEmails = (emails) => {
        const getUrgencyValue = (email) => {
            const urgencyBlock = email.analysis_json?.['邮件紧急程度评估'] || email.analysis_json?.['郵件緊急程度評估'];
            const urgency = urgencyBlock?.[0]?.['- **紧急程度**'] || urgencyBlock?.[0]?.['- **緊急程度**'];
            switch (urgency) {
                case '高': return 1;
                case '中': return 2;
                case '低': return 3;
                default: return 4;
            }
        };

        const getTitleTypeValue = (title) => {
            if (/^\d/.test(title)) return 1;
            if (/^[a-zA-Z]/.test(title)) return 2;
            if (/^[\u4e00-\u9fa5]/.test(title)) return 3;
            return 4;
        };

        return [...emails].sort((a, b) => {
            const urgencyA = getUrgencyValue(a);
            const urgencyB = getUrgencyValue(b);
            if (urgencyA !== urgencyB) {
                return urgencyA - urgencyB;
            }

            const summaryBlockA = a.analysis_json?.['邮件摘要'] || a.analysis_json?.['郵件摘要'];
            const summaryA = summaryBlockA?.[0]?.['**主题**'] || summaryBlockA?.[0]?.['**主題**'] || a.subject;
            const summaryBlockB = b.analysis_json?.['邮件摘要'] || b.analysis_json?.['郵件摘要'];
            const summaryB = summaryBlockB?.[0]?.['**主题**'] || summaryBlockB?.[0]?.['**主題**'] || b.subject;

            const titleTypeA = getTitleTypeValue(summaryA);
            const titleTypeB = getTitleTypeValue(summaryB);
            if (titleTypeA !== titleTypeB) {
                return titleTypeA - titleTypeB;
            }

            return summaryA.localeCompare(summaryB, 'zh-Hans-CN');
        });
    };

    return (
        <div className="sidebar">
            <div className="sidebar-header">
                <h2>收件箱</h2>
                <div className="header-buttons">
                    <button onClick={onSync} className="sync-button">同步</button>
                    <button onClick={onShowSettings} className="settings-button">设置</button>
                </div>
            </div>
            <div className="filter-container">
                <label htmlFor="urgency-filter">筛选紧急程度: </label>
                <select id="urgency-filter" value={urgencyFilter} onChange={e => onFilterChange(e.target.value)}>
                    <option value="all">全部</option>
                    <option value="高">高</option>
                    <option value="中">中</option>
                    <option value="低">低</option>
                </select>
            </div>
            <div className="email-list">
                {Object.keys(groupedEmails).sort((a, b) => b - a).map(year => {
                    const monthKeys = Object.keys(groupedEmails[year]).map(m => `${year}-${m}`);
                    const areAnyMonthsExpanded = monthKeys.some(key => expanded[key]);
                    return (
                        <div key={year} className="year-group">
                            <h3 onClick={() => toggleExpand(year)} className="collapsible">
                                <span>{expanded[year] ? '[-]' : '[+]'} {year}</span>
                                <button onClick={(e) => toggleAllChildren(e, monthKeys)} className="toggle-all-btn">
                                    {areAnyMonthsExpanded ? '收起' : '展开'}
                                </button>
                            </h3>
                            {expanded[year] && Object.keys(groupedEmails[year]).sort((a, b) => b - a).map(month => {
                                const dayKeys = Object.keys(groupedEmails[year][month]).map(d => `${year}-${month}-${d}`);
                                const areAnyDaysExpanded = dayKeys.some(key => expanded[key]);
                                return (
                                    <div key={`${year}-${month}`} className="month-group">
                                        <h4 onClick={() => toggleExpand(`${year}-${month}`)} className="collapsible">
                                            <span>{expanded[`${year}-${month}`] ? '[-]' : '[+]'} {month}月</span>
                                            <button onClick={(e) => toggleAllChildren(e, dayKeys)} className="toggle-all-btn">
                                                {areAnyDaysExpanded ? '收起' : '展开'}
                                            </button>
                                        </h4>
                                        {expanded[`${year}-${month}`] && Object.keys(groupedEmails[year][month]).sort((a, b) => b - a).map(day => (
                                            <div key={`${year}-${month}-${day}`} className="day-group">
                                                <h5 onClick={() => toggleExpand(`${year}-${month}-${day}`)} className="collapsible">
                                                    <span>{expanded[`${year}-${month}-${day}`] ? '[-]' : '[+]'} {day}日</span>
                                                </h5>
                                                {expanded[`${year}-${month}-${day}`] && sortEmails(groupedEmails[year][month][day]).map(email => {
                                                    const summaryBlock = email.analysis_json?.['邮件摘要'] || email.analysis_json?.['郵件摘要'];
                                                    const summary = summaryBlock?.[0]?.['**主题**'] || summaryBlock?.[0]?.['**主題**'] || email.subject;
                                                    return (
                                                        <div key={email.id} className="email-item" onClick={() => onSelectEmail(email)}>
                                                            <div className={`email-subject ${getUrgencyClass(email)}`}>{summary}</div>
                                                            <div className="email-from">{email.from_name || email.from_email}</div>
                                                        </div>
                                                    );
                                                })}
                                            </div>
                                        ))}
                                    </div>
                                );
                            })}
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

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

const EmailBody = ({ raw_email_body }) => {
    const [modalImageSrc, setModalImageSrc] = useState(null);
    const contentRef = React.useRef(null);
    const containerRef = React.useRef(null);

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
    }, [raw_email_body]);

    useEffect(() => {
        if (containerRef.current) {
            containerRef.current.scrollTop = 0;
        }
    }, [raw_email_body]);

    return (
        <>
            <div ref={containerRef} className="email-body-container">
                <h3>原文</h3>
                <div ref={contentRef} className="email-body-content" dangerouslySetInnerHTML={{ __html: raw_email_body }} />
            </div>
            <ImageModal src={modalImageSrc} onClose={() => setModalImageSrc(null)} />
        </>
    );
};

const EmailAnalysis = ({ analysis_markdown }) => {
    const containerRef = React.useRef(null);

    useEffect(() => {
        if (containerRef.current) {
            containerRef.current.scrollTop = 0;
        }
    }, [analysis_markdown]);

    // 配置 marked 以更好地处理换行
    marked.setOptions({
        breaks: true,
    });

    const getMarkdownText = () => {
        const rawMarkup = marked(analysis_markdown || '');
        return { __html: rawMarkup };
    };

    return (
        <div ref={containerRef} className="email-analysis-container">
            <h3>分析结果</h3>
            <div className="email-analysis-content" dangerouslySetInnerHTML={getMarkdownText()} />
        </div>
    );
};


const EmailDetail = ({ email }) => {
    if (!email) {
        return <div className="email-detail-placeholder">请在左侧选择一封邮件查看详情</div>;
    }

    return (
        <div className="email-detail-view">
            <EmailBody raw_email_body={email.raw_email_body} />
            <EmailAnalysis analysis_markdown={email.analysis_markdown} />
        </div>
    );
};


const SyncLogModal = ({ logs, show, onClose }) => {
    const logContentRef = React.useRef(null);

    // 自动滚动到日志底部
    useEffect(() => {
        if (logContentRef.current) {
            logContentRef.current.scrollTop = logContentRef.current.scrollHeight;
        }
    }, [logs]);

    if (!show) return null;

    return (
        <div className="sync-log-modal-backdrop">
            <div className="sync-log-modal-content">
                <h3>同步日志</h3>
                <pre ref={logContentRef} className="sync-log-output">
                    {logs.join('\n')}
                </pre>
                <button onClick={onClose} className="close-log-button">关闭</button>
            </div>
        </div>
    );
};


function App() {
    const [emails, setEmails] = useState([]);
    const [selectedEmail, setSelectedEmail] = useState(null);
    const [urgencyFilter, setUrgencyFilter] = useState('all'); // 'all', '高', '中', '低'
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showSettings, setShowSettings] = useState(false); // 控制是否显示设置页面
    const [showSyncLog, setShowSyncLog] = useState(false);
    const [syncLogs, setSyncLogs] = useState([]);

    const fetchEmails = useCallback(async () => {
        try {
            setLoading(true);
            const response = await fetch('http://localhost:5001/api/emails');
            if (!response.ok) {
                throw new Error(`HTTP 错误! 状态: ${response.status}`);
            }
            const data = await response.json();
            setEmails(data);
        } catch (e) {
            setError(e.message);
            console.error("获取邮件失败:", e);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        if (!showSettings) { // 只在不在设置页面时才加载邮件
            fetchEmails();
        }
    }, [fetchEmails, showSettings]);

    const handleSync = () => {
        setSyncLogs([]);
        setShowSyncLog(true);

        const eventSource = new EventSource('http://localhost:5001/api/sync-emails', {
            method: 'POST', // EventSource 不直接支持POST，但我们可以通过后端配置接受GET请求
        });

        eventSource.onmessage = (event) => {
            const logLine = event.data;

            if (logLine.startsWith('ERROR:')) {
                setSyncLogs(prev => [...prev, logLine]);
                eventSource.close();
                // 可以在这里添加一个关闭按钮的逻辑
            } else if (logLine === 'SYNC_COMPLETE') {
                setSyncLogs(prev => [...prev, '--- 同步成功完成！---']);
                eventSource.close();
                // 刷新邮件数据
                fetchEmails();
                // 2秒后自动关闭模态框
                setTimeout(() => {
                    setShowSyncLog(false);
                }, 2000);
            } else {
                setSyncLogs(prev => [...prev, logLine]);
            }
        };

        eventSource.onerror = (err) => {
            console.error("EventSource 失败:", err);
            setSyncLogs(prev => [...prev, '--- 连接错误，同步中断 ---']);
            eventSource.close();
        };
    };

    const filteredEmails = useMemo(() => {
        if (urgencyFilter === 'all') {
            return emails;
        }
        return emails.filter(email => {
            const urgencyBlock = email.analysis_json?.['邮件紧急程度评估'] || email.analysis_json?.['郵件緊急程度評估'];
            const urgency = urgencyBlock?.[0]?.['- **紧急程度**'] || urgencyBlock?.[0]?.['- **緊急程度**'];
            return urgency === urgencyFilter;
        });
    }, [emails, urgencyFilter]);

    const groupedEmails = useMemo(() => {
        const groups = {};
        filteredEmails.forEach(email => {
            try {
                const date = new Date(email.received_date);
                if (isNaN(date.getTime())) {
                    console.warn(`邮件ID ${email.id} 的日期格式无效: ${email.received_date}`);
                    return;
                }
                const year = date.getFullYear();
                const month = date.getMonth() + 1;
                const day = date.getDate();

                if (!groups[year]) groups[year] = {};
                if (!groups[year][month]) groups[year][month] = {};
                if (!groups[year][month][day]) groups[year][month][day] = [];

                groups[year][month][day].push(email);
            } catch (e) {
                console.error(`处理邮件ID ${email.id} 的日期时出错:`, e);
            }
        });
        return groups;
    }, [filteredEmails]);

    if (loading) return <div className="app-status">正在加载邮件...</div>;
    if (error) return <div className="app-status error">加载失败: {error}</div>;

    return (
        <div className="App">
            <SyncLogModal 
                show={showSyncLog} 
                logs={syncLogs} 
                onClose={() => setShowSyncLog(false)} 
            />
            {showSettings ? (
                <SettingsPage onBack={() => setShowSettings(false)} />
            ) : (
                <>
                    <Sidebar 
                        groupedEmails={groupedEmails} 
                        onSelectEmail={setSelectedEmail}
                        onFilterChange={setUrgencyFilter}
                        urgencyFilter={urgencyFilter}
                        onSync={handleSync}
                        onShowSettings={() => setShowSettings(true)}
                    />
                    <main className="main-content">
                        <EmailDetail email={selectedEmail} />
                    </main>
                </>
            )}
        </div>
    );
}

export default App;
