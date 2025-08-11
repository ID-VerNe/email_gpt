import React, { useState } from 'react';
import './Sidebar.css';

const Sidebar = ({ groupedEmails, onSelectEmail, onFilterChange, onSync, onShowSettings }) => {
    const [expanded, setExpanded] = useState(() => {
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

    const {
        onUrgencyCycle,
        onReadCycle,
        onStarredCycle,
        urgencyFilter,
        readFilter,
        starredFilter
    } = onFilterChange;

    const getUrgencyButtonText = () => {
        const map = { 'all': '全', '高': '高', '中': '中', '低': '低' };
        return map[urgencyFilter];
    };

    const getReadButtonText = () => {
        const map = { 'all': '全部', 'read': '已读', 'unread': '未读' };
        return map[readFilter];
    };

    const getStarredButtonText = () => {
        const map = { 'all': '全部', 'starred': '加星' };
        return map[starredFilter];
    };

    const renderEmailItem = (email) => {
        const summaryBlock = email.analysis_json?.['邮件摘要'] || email.analysis_json?.['郵件摘要'];
        const summary = summaryBlock?.[0]?.['**主题**'] || summaryBlock?.[0]?.['**主題**'] || email.subject;
        return (
            <div key={email.id} className={`email-item ${email.is_read ? 'email-read' : ''}`} onClick={() => onSelectEmail(email)}>
                <div className="email-item-header">
                    <div className={`email-subject ${getUrgencyClass(email)}`}>{summary}</div>
                    {email.is_starred ? <span className="star-icon">★</span> : null}
                </div>
                <div className="email-from">{email.from_name || email.from_email}</div>
            </div>
        );
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
            <div className="filter-container-single">
                <button onClick={onUrgencyCycle} className={`filter-button-single urgency-${urgencyFilter}`}>
                    {getUrgencyButtonText()}
                </button>
                <button onClick={onReadCycle} className={`filter-button-single read-${readFilter}`}>
                    {getReadButtonText()}
                </button>
                <button onClick={onStarredCycle} className={`filter-button-single starred-${starredFilter}`}>
                    {getStarredButtonText()}
                </button>
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
                                                {expanded[`${year}-${month}-${day}`] && sortEmails(groupedEmails[year][month][day]).map(email => renderEmailItem(email))}
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

export default Sidebar;
