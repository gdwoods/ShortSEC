"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Loader2, ArrowLeft } from "lucide-react";

interface CompanyActivity {
  id: string;
  ticker?: string;
  activity_type?: string;
  description?: string;
  date?: string;
  created_at?: string;
  [key: string]: any; // Allow for additional fields
}

interface PaginationInfo {
  page: number;
  limit: number;
  total: number;
  totalPages: number;
}

export default function CompanyActivitiesPage() {
  const [activities, setActivities] = useState<CompanyActivity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pagination, setPagination] = useState<PaginationInfo>({
    page: 1,
    limit: 50,
    total: 0,
    totalPages: 0,
  });
  const [tickerFilter, setTickerFilter] = useState("");
  const [sortBy, setSortBy] = useState("ticker");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");

  const fetchActivities = async () => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        page: pagination.page.toString(),
        limit: pagination.limit.toString(),
        sortBy,
        sortOrder,
      });

      if (tickerFilter.trim()) {
        params.append("ticker", tickerFilter.trim().toUpperCase());
      }

      const response = await fetch(`/api/company-activities?${params.toString()}`);
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Failed to fetch activities");
      }

      const result = await response.json();
      setActivities(result.data || []);
      setPagination(result.pagination || pagination);
    } catch (err) {
      console.error("Error fetching activities:", err);
      setError(err instanceof Error ? err.message : "Failed to load activities");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchActivities();
  }, [pagination.page, sortBy, sortOrder, tickerFilter]);

  const handlePageChange = (newPage: number) => {
    setPagination((prev) => ({ ...prev, page: newPage }));
  };

  const handleSort = (field: string) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortBy(field);
      setSortOrder("desc");
    }
  };

  // Format date/datetime values
  const formatDateValue = (value: any, colName: string): string => {
    if (!value || value === "-") return "-";
    
    try {
      const date = new Date(value);
      if (isNaN(date.getTime())) return String(value);
      
      // Check if it's a datetime (has time component) or just a date
      const isDatetime = String(value).includes('T') || String(value).includes(' ');
      
      if (isDatetime) {
        // Format as date with time
        return date.toLocaleString('en-US', {
          month: 'short',
          day: 'numeric',
          year: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
          hour12: true
        });
      } else {
        // Format as date only
        return date.toLocaleDateString('en-US', {
          month: 'short',
          day: 'numeric',
          year: 'numeric'
        });
      }
    } catch {
      return String(value);
    }
  };

  // Check if a column is a date/datetime column
  const isDateColumn = (colName: string, value: any): boolean => {
    const dateKeywords = ['date', 'time', 'created', 'updated', 'notification', 'timestamp'];
    const lowerCol = colName.toLowerCase();
    
    // Check column name
    if (dateKeywords.some(keyword => lowerCol.includes(keyword))) {
      return true;
    }
    
    // Check value format if it looks like a date string
    if (value && typeof value === 'string') {
      // ISO datetime format
      if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/.test(value)) return true;
      // Date format
      if (/^\d{4}-\d{2}-\d{2}/.test(value)) return true;
      // Common date formats
      if (/^\d{1,2}\/\d{1,2}\/\d{4}/.test(value)) return true;
    }
    
    return false;
  };

  // Get all unique column names from activities
  // Exclude: email_id, message_id, id, created_at, Source
  // Put ticker first
  const getColumns = (): string[] => {
    if (activities.length === 0) return [];
    const excludedColumns = new Set(['email_id', 'message_id', 'id', 'created_at', 'Source']);
    const allKeys = new Set<string>();
    activities.forEach((activity) => {
      Object.keys(activity).forEach((key) => {
        if (!excludedColumns.has(key)) {
          allKeys.add(key);
        }
      });
    });
    
    // Put ticker first, then sort the rest
    const columns = Array.from(allKeys);
    const tickerIndex = columns.indexOf('ticker');
    if (tickerIndex > -1) {
      columns.splice(tickerIndex, 1);
      return ['ticker', ...columns.sort()];
    }
    return columns.sort();
  };

  const columns = getColumns();

  return (
    <div className="min-h-screen p-6 bg-gray-100 dark:bg-gray-900">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="p-2 rounded-lg bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors text-gray-700 dark:text-gray-300"
            >
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div>
              <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">Company Activities</h1>
              <p className="text-gray-600 dark:text-gray-400">
                View all company activities tracked in the system
              </p>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
          <div className="flex gap-4 items-center flex-wrap">
            <div className="flex items-center gap-2">
              <label htmlFor="ticker-filter" className="font-medium text-gray-900 dark:text-white">
                Filter by Ticker:
              </label>
              <input
                id="ticker-filter"
                type="text"
                value={tickerFilter}
                onChange={(e) => {
                  setTickerFilter(e.target.value);
                  setPagination((prev) => ({ ...prev, page: 1 }));
                }}
                placeholder="e.g., AAPL"
                className="border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white px-3 py-2 rounded w-32 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="flex items-center gap-2">
              <label htmlFor="sort-by" className="font-medium text-gray-900 dark:text-white">
                Sort by:
              </label>
              <select
                id="sort-by"
                value={sortBy}
                onChange={(e) => {
                  setSortBy(e.target.value);
                  setPagination((prev) => ({ ...prev, page: 1 }));
                }}
                className="border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white px-3 py-2 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {columns.map((col) => (
                  <option key={col} value={col}>
                    {col.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())}
                  </option>
                ))}
              </select>
              <button
                onClick={() => {
                  setSortOrder(sortOrder === "asc" ? "desc" : "asc");
                  setPagination((prev) => ({ ...prev, page: 1 }));
                }}
                className="px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"
              >
                {sortOrder === "asc" ? "↑" : "↓"}
              </button>
            </div>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-900/20 border border-red-800 rounded-lg p-6">
            <div className="flex items-center gap-2 text-red-400 mb-2">
              <h3 className="font-semibold">Error</h3>
            </div>
            <p className="text-red-300">{error}</p>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="bg-white dark:bg-gray-800 rounded-lg p-12 text-center border border-gray-200 dark:border-gray-700">
            <Loader2 className="w-8 h-8 text-blue-600 dark:text-blue-400 animate-spin mx-auto mb-4" />
            <p className="text-gray-600 dark:text-gray-400">Loading activities...</p>
          </div>
        )}

        {/* Table */}
        {!loading && !error && (
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full border-collapse">
                <thead>
                  <tr className="bg-gray-100 dark:bg-gray-700">
                    {columns.map((col) => (
                      <th
                        key={col}
                        className="border border-gray-300 dark:border-gray-600 px-4 py-3 text-left cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors text-gray-900 dark:text-white font-semibold"
                        onClick={() => handleSort(col)}
                      >
                        <div className="flex items-center gap-2">
                          {col.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())}
                          {sortBy === col && (
                            <span className="text-blue-600 dark:text-blue-400">{sortOrder === "asc" ? "↑" : "↓"}</span>
                          )}
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {activities.length === 0 ? (
                    <tr>
                      <td
                        colSpan={columns.length}
                        className="border border-gray-300 dark:border-gray-600 px-4 py-8 text-center text-gray-500 dark:text-gray-400"
                      >
                        No activities found
                      </td>
                    </tr>
                  ) : (
                    activities.map((activity) => (
                      <tr key={activity.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                        {columns.map((col) => {
                          const rawValue = activity[col];
                          
                          // Check if this is a date column and format it
                          const isDate = isDateColumn(col, rawValue);
                          const cellValue = isDate 
                            ? formatDateValue(rawValue, col)
                            : rawValue !== null && rawValue !== undefined
                              ? typeof rawValue === "object"
                                ? JSON.stringify(rawValue)
                                : String(rawValue)
                              : "-";
                          
                          // Special handling for text columns that might be long (like description)
                          const isTextColumn = !isDate && (
                            col === 'description' || col === 'email_subject' || 
                            col.toLowerCase().includes('description') || 
                            col.toLowerCase().includes('subject') ||
                            col.toLowerCase().includes('message')
                          );
                          
                          return (
                            <td
                              key={col}
                              className={`border border-gray-300 dark:border-gray-600 px-4 py-2 text-gray-900 dark:text-white ${
                                isTextColumn ? 'max-w-md' : isDate ? 'whitespace-nowrap' : ''
                              }`}
                              title={isTextColumn && cellValue !== '-' ? String(rawValue) : 
                                     isDate && rawValue ? String(rawValue) : undefined}
                            >
                              {isTextColumn ? (
                                <div className="line-clamp-2 break-words">
                                  {cellValue}
                                </div>
                              ) : (
                                cellValue
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {pagination.totalPages > 1 && (
              <div className="bg-gray-50 dark:bg-gray-700/50 px-4 py-3 flex justify-between items-center border-t border-gray-200 dark:border-gray-600">
                <div className="text-sm text-gray-600 dark:text-gray-400">
                  Showing {((pagination.page - 1) * pagination.limit) + 1} to{" "}
                  {Math.min(pagination.page * pagination.limit, pagination.total)} of{" "}
                  {pagination.total} activities
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handlePageChange(pagination.page - 1)}
                    disabled={pagination.page === 1}
                    className="px-4 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"
                  >
                    Previous
                  </button>
                  <span className="px-4 py-2 text-gray-900 dark:text-white">
                    Page {pagination.page} of {pagination.totalPages}
                  </span>
                  <button
                    onClick={() => handlePageChange(pagination.page + 1)}
                    disabled={pagination.page >= pagination.totalPages}
                    className="px-4 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
