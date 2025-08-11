import React, { useState, useEffect, useMemo, useCallback } from 'react';
import './App.css';
import SettingsPage from './SettingsPage';
import SearchBar from './components/SearchBar';
import Sidebar from './components/Sidebar';
import EmailDetail from './components/EmailDetail';
import SyncLogModal from './components/SyncLogModal';

function App() {
    const [emails, setEmails] = useState([]);
    const [selectedEmail, setSelectedEmail] = useState(null);
    const [urgencyFilter, setUrgencyFilter] = useState('all');
    const [readFilter, setReadFilter] = useState('all');
    const [starredFilter, setStarredFilter] = useState('all');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showSettings, setShowSettings] = useState(false);
    const [showSyncLog, setShowSyncLog] = useState(false);
    const [syncLogs, setSyncLogs] = useState([]);
    const [searchQuery, setSearchQuery] = useState('');
    const [debouncedQuery, setDebouncedQuery] = useState('');
    const [searchResults, setSearchResults] = useState([]);
    const [isSearching, setIsSearching] = useState(false);

    // Debounce search input
    useEffect(() => {
        const handler = setTimeout(() => {
            setDebouncedQuery(searchQuery);
        }, 1000); // 1-second delay

        return () => {
            clearTimeout(handler);
        };
    }, [searchQuery]);

    // Perform search when debounced query changes
    useEffect(() => {
        if (debouncedQuery) {
            setIsSearching(true);
            fetch(`http://localhost:5001/api/search?query=${encodeURIComponent(debouncedQuery)}`)
                .then(response => response.json())
                .then(data => {
                    setSearchResults(data);
                    setIsSearching(false);
                })
                .catch(err => {
                    console.error("搜索失败:", err);
                    setError("搜索失败");
                    setIsSearching(false);
                });
        } else {
            setSearchResults([]);
        }
    }, [debouncedQuery]);

    const handleUrgencyCycle = () => {
        const states = ['all', '高', '中', '低'];
        setUrgencyFilter(s => states[(states.indexOf(s) + 1) % states.length]);
    };

    const handleReadCycle = () => {
        const states = ['all', 'unread', 'read'];
        setReadFilter(s => states[(states.indexOf(s) + 1) % states.length]);
    };

    const handleStarredCycle = () => {
        const states = ['all', 'starred'];
        setStarredFilter(s => states[(states.indexOf(s) + 1) % states.length]);
    };

    const handleUpdateEmailStatus = useCallback(async (emailId, updates) => {
        try {
            const response = await fetch(`http://localhost:5001/api/emails/${emailId}/status`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updates),
            });
            if (!response.ok) throw new Error(`HTTP 错误! 状态: ${response.status}`);
            const updatedEmail = await response.json();
            
            const updateList = (list) => list.map(e => e.id === emailId ? updatedEmail : e);
            setEmails(prev => updateList(prev));
            setSearchResults(prev => updateList(prev));
            if (selectedEmail?.id === emailId) {
                setSelectedEmail(updatedEmail);
            }
        } catch (e) {
            console.error("更新邮件状态失败:", e);
            setError(e.message);
        }
    }, [selectedEmail]);

    const handleUpdateUrgency = useCallback(async (emailId, newUrgency) => {
        try {
            const response = await fetch(`http://localhost:5001/api/emails/${emailId}/urgency`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ urgency: newUrgency }),
            });
            if (!response.ok) throw new Error(`HTTP 错误! 状态: ${response.status}`);
            const updatedEmail = await response.json();

            const updateList = (list) => list.map(e => e.id === emailId ? updatedEmail : e);
            setEmails(prev => updateList(prev));
            setSearchResults(prev => updateList(prev));
            if (selectedEmail?.id === emailId) {
                setSelectedEmail(updatedEmail);
            }
        } catch (e) {
            console.error("更新邮件紧急程度失败:", e);
            setError(e.message);
        }
    }, [selectedEmail]);

    const handleSelectEmail = (email) => {
        if (email && !email.is_read) {
            handleUpdateEmailStatus(email.id, { is_read: true });
        }
        setSelectedEmail(email);
    };

    const fetchEmails = useCallback(async () => {
        try {
            setLoading(true);
            const response = await fetch('http://localhost:5001/api/emails');
            if (!response.ok) throw new Error(`HTTP 错误! 状态: ${response.status}`);
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
        if (!showSettings) {
            fetchEmails();
        }
    }, [fetchEmails, showSettings]);

    const handleSync = () => {
        setSyncLogs([]);
        setShowSyncLog(true);
        const eventSource = new EventSource('http://localhost:5001/api/sync-emails');
        eventSource.onmessage = (event) => {
            const logLine = event.data;
            if (logLine.startsWith('ERROR:')) {
                setSyncLogs(prev => [...prev, logLine]);
                eventSource.close();
            } else if (logLine === 'SYNC_COMPLETE') {
                setSyncLogs(prev => [...prev, '--- 同步成功完成！---']);
                eventSource.close();
                fetchEmails();
                setSelectedEmail(null);
                setTimeout(() => setShowSyncLog(false), 2000);
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
        return emails.filter(email => {
            const urgencyBlock = email.analysis_json?.['邮件紧急程度评估'] || email.analysis_json?.['郵件緊急程度評估'];
            const urgency = urgencyBlock?.[0]?.['- **紧急程度**'] || urgencyBlock?.[0]?.['- **緊急程度**'];
            const matchesUrgency = urgencyFilter === 'all' || urgency === urgencyFilter;
            const matchesReadStatus = readFilter === 'all' || (readFilter === 'read' && email.is_read) || (readFilter === 'unread' && !email.is_read);
            const matchesStarredStatus = starredFilter === 'all' || (starredFilter === 'starred' && email.is_starred);
            return matchesUrgency && matchesReadStatus && matchesStarredStatus;
        });
    }, [emails, urgencyFilter, readFilter, starredFilter]);

    const groupedEmails = useMemo(() => {
        const groups = {};
        filteredEmails.forEach(email => {
            try {
                const date = new Date(email.received_date);
                if (isNaN(date.getTime())) return;
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
            <SearchBar 
                query={searchQuery} 
                setQuery={setSearchQuery}
                searchResults={searchResults}
                onSelectEmail={handleSelectEmail}
                isSearching={isSearching}
            />
            <div className="main-layout">
                {showSettings ? (
                    <SettingsPage onBack={() => setShowSettings(false)} />
                ) : (
                    <>
                        <Sidebar 
                            groupedEmails={groupedEmails} 
                            onSelectEmail={handleSelectEmail}
                            onFilterChange={{
                                onUrgencyCycle: handleUrgencyCycle,
                                onReadCycle: handleReadCycle,
                                onStarredCycle: handleStarredCycle,
                                urgencyFilter,
                                readFilter,
                                starredFilter
                            }}
                            onSync={handleSync}
                            onShowSettings={() => setShowSettings(true)}
                        />
                        <main className="main-content">
                            <EmailDetail 
                                email={selectedEmail} 
                                onUpdateEmail={handleUpdateEmailStatus} 
                                onUpdateUrgency={handleUpdateUrgency} 
                                searchQuery={debouncedQuery}
                            />
                        </main>
                    </>
                )}
            </div>
        </div>
    );
}

export default App;
