"use client";

import { useState, useEffect } from "react";
import { DilutionAlert } from "@/types/alert";
import { ExternalLink, Star } from "lucide-react";
import { hasValidUnderwriter } from "@/lib/alertUtils";
import FormTypeTooltip from "@/components/FormTypeTooltip";
import { isTickerWatched, toggleWatchlist } from "@/lib/watchlist";

interface AlertTableProps {
  alerts: DilutionAlert[];
  onRowClick?: (alert: DilutionAlert) => void;
  onWatchlistChange?: () => void;
}

export default function AlertTable({ alerts, onRowClick, onWatchlistChange }: AlertTableProps) {
  const [watchedTickers, setWatchedTickers] = useState<Set<string>>(new Set());

  // Load watchlist state for all unique tickers in alerts
  useEffect(() => {
    const loadWatchlistState = async () => {
      const uniqueTickers = [...new Set(alerts.map(a => a.ticker.toUpperCase()))];
      const watchlistChecks = await Promise.all(
        uniqueTickers.map(ticker => isTickerWatched(ticker).then(watched => ({ ticker, watched })))
      );
      const watchedSet = new Set(
        watchlistChecks.filter(check => check.watched).map(check => check.ticker)
      );
      setWatchedTickers(watchedSet);
    };

    if (alerts.length > 0) {
      loadWatchlistState();
    }
  }, [alerts]);

  const handleWatchlistToggle = async (ticker: string, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent row click
    const tickerUpper = ticker.toUpperCase();
    const success = await toggleWatchlist(tickerUpper);
    if (success) {
      const isWatched = watchedTickers.has(tickerUpper);
      setWatchedTickers(prev => {
        const next = new Set(prev);
        if (isWatched) {
          next.delete(tickerUpper);
        } else {
          next.add(tickerUpper);
        }
        return next;
      });
      onWatchlistChange?.();
    }
  };

  if (!alerts || alerts.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg p-8 text-center border border-gray-200 dark:border-gray-700">
        <p className="text-gray-600 dark:text-gray-400">No alerts found</p>
      </div>
    );
  }

  const getRiskColor = (score: number) => {
    if (score >= 15) return "text-red-400";
    if (score >= 10) return "text-orange-400";
    if (score >= 5) return "text-yellow-400";
    return "text-green-400";
  };

  const formatCurrency = (value: string | null) => {
    if (!value) return "-";
    try {
      const num = parseFloat(value.replace(/[$,]/g, ""));
      if (num >= 1_000_000) {
        return `$${(num / 1_000_000).toFixed(1)}M`;
      }
      return value;
    } catch {
      return value;
    }
  };

  // Format date without timezone conversion (to prevent date shifting)
  const formatDate = (dateStr: string | null | undefined) => {
    if (!dateStr) return "";
    // If date is in YYYY-MM-DD format, parse as local date (not UTC)
    if (dateStr.match(/^\d{4}-\d{2}-\d{2}$/)) {
      const [year, month, day] = dateStr.split("-").map(Number);
      const date = new Date(year, month - 1, day); // month is 0-indexed
      return date.toLocaleDateString();
    }
    // Otherwise, use Date constructor (may have timezone issues)
    return new Date(dateStr).toLocaleDateString();
  };

  // Format datetime, preserving the date part correctly
  const formatDateTime = (datetimeStr: string | null | undefined) => {
    if (!datetimeStr) return null;
    try {
      // If it's an ISO datetime string, extract the date part
      if (datetimeStr.includes("T")) {
        const datePart = datetimeStr.split("T")[0];
        const timePart = datetimeStr.split("T")[1]?.split(/[+\-Z]/)[0]; // Remove timezone
        const [year, month, day] = datePart.split("-").map(Number);
        const [hours, minutes] = timePart ? timePart.split(":").map(Number) : [0, 0];
        const date = new Date(year, month - 1, day, hours, minutes);
        return {
          date: date.toLocaleDateString(),
          time: date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };
      }
      // Fallback
      const date = new Date(datetimeStr);
      return {
        date: date.toLocaleDateString(),
        time: date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
    } catch {
      return null;
    }
  };

  // Check if a filing is from today
  const isNewToday = (alert: DilutionAlert): boolean => {
    try {
      const today = new Date();
      today.setHours(0, 0, 0, 0); // Start of today

      // Check filing_datetime first (more precise)
      if (alert.filing_datetime) {
        let filingDate: Date;
        if (alert.filing_datetime.includes("T")) {
          const datePart = alert.filing_datetime.split("T")[0];
          const [year, month, day] = datePart.split("-").map(Number);
          filingDate = new Date(year, month - 1, day);
        } else {
          filingDate = new Date(alert.filing_datetime);
        }
        filingDate.setHours(0, 0, 0, 0);
        return filingDate.getTime() === today.getTime();
      }

      // Fallback to date field
      if (alert.date) {
        if (alert.date.match(/^\d{4}-\d{2}-\d{2}$/)) {
          const [year, month, day] = alert.date.split("-").map(Number);
          const filingDate = new Date(year, month - 1, day);
          filingDate.setHours(0, 0, 0, 0);
          return filingDate.getTime() === today.getTime();
        }
        const filingDate = new Date(alert.date);
        filingDate.setHours(0, 0, 0, 0);
        return filingDate.getTime() === today.getTime();
      }

      return false;
    } catch {
      return false;
    }
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-xs table-fixed">
        <colgroup>
          <col className="w-[70px]" />
          <col className="w-[75px]" />
          <col className="w-[45px]" />
          <col className="w-[70px]" />
          <col className="w-[40px]" />
          <col className="w-[85px]" />
          <col className="w-[60px]" />
          <col className="w-[65px]" />
          <col className="w-[70px]" />
          <col className="w-[120px]" />
          <col className="w-[35px]" />
        </colgroup>
        <thead>
          <tr className="border-b border-gray-200 dark:border-gray-700">
            <th className="text-left px-1 py-1 font-medium text-gray-600 dark:text-gray-400 whitespace-nowrap">Date</th>
            <th className="text-left px-1 py-1 font-medium text-gray-600 dark:text-gray-400 whitespace-nowrap">Ticker</th>
            <th className="text-left px-1 py-1 font-medium text-gray-600 dark:text-gray-400 whitespace-nowrap">Form</th>
            <th className="text-left px-1 py-1 font-medium text-gray-600 dark:text-gray-400 whitespace-nowrap">Type</th>
            <th className="text-left px-1 py-1 font-medium text-gray-600 dark:text-gray-400 whitespace-nowrap">Risk</th>
            <th className="text-left px-1 py-1 font-medium text-gray-600 dark:text-gray-400 whitespace-nowrap">Stock Price</th>
            <th className="text-left px-1 py-1 font-medium text-gray-600 dark:text-gray-400 whitespace-nowrap">Share Price</th>
            <th className="text-left px-1 py-1 font-medium text-gray-600 dark:text-gray-400 whitespace-nowrap">Offering</th>
            <th className="text-left px-1 py-1 font-medium text-gray-600 dark:text-gray-400 whitespace-nowrap">Shares</th>
            <th className="text-left px-1 py-1 font-medium text-gray-600 dark:text-gray-400 whitespace-nowrap">Flags</th>
            <th className="text-left px-1 py-1 font-medium text-gray-600 dark:text-gray-400 whitespace-nowrap">Details</th>
          </tr>
        </thead>
        <tbody>
          {alerts.map((alert) => (
            <tr
              key={alert.id}
              onClick={() => onRowClick?.(alert)}
              className={`border-b border-gray-200 dark:border-gray-800 transition-colors ${
                onRowClick ? "cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800/70" : "hover:bg-gray-50 dark:hover:bg-gray-800/50"
              }`}
            >
              <td className="px-1 py-0.5 text-gray-700 dark:text-gray-300">
                <div className="flex items-center gap-0.5">
                  <div className="whitespace-nowrap">
                    {alert.filing_datetime ? (
                      (() => {
                        const dt = formatDateTime(alert.filing_datetime);
                        return dt ? (
                          <>
                            <div className="text-xs">{dt.date}</div>
                            <div className="text-[10px] text-gray-500 dark:text-gray-500">
                              {dt.time}
                            </div>
                          </>
                        ) : (
                          <div className="text-xs">{formatDate(alert.date)}</div>
                        );
                      })()
                    ) : (
                      <div className="text-xs">{formatDate(alert.date)}</div>
                    )}
                  </div>
                  {isNewToday(alert) && (
                    <span className="text-[10px] px-0.5 py-0 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded font-medium whitespace-nowrap">
                      New
                    </span>
                  )}
                </div>
              </td>
              <td className="px-1 py-0.5">
                <div className="flex items-center gap-0.5">
                  <div>
                    <a
                      href={`/company/${alert.ticker}`}
                      onClick={(e) => e.stopPropagation()}
                      className="font-semibold text-gray-900 dark:text-white hover:text-blue-600 dark:hover:text-blue-400 hover:underline whitespace-nowrap"
                    >
                      {alert.ticker}
                    </a>
                    {alert.company_name && (
                      <div className="text-[10px] text-gray-500 dark:text-gray-500 truncate max-w-[120px]" title={alert.company_name}>
                        {alert.company_name}
                      </div>
                    )}
                  </div>
                  <button
                    onClick={(e) => handleWatchlistToggle(alert.ticker, e)}
                    className={`p-0 rounded transition-colors ${
                      watchedTickers.has(alert.ticker.toUpperCase())
                        ? "text-yellow-500 dark:text-yellow-400 hover:text-yellow-600 dark:hover:text-yellow-300"
                        : "text-gray-400 dark:text-gray-500 hover:text-yellow-500 dark:hover:text-yellow-400"
                    }`}
                    title={watchedTickers.has(alert.ticker.toUpperCase()) ? "Remove from watchlist" : "Add to watchlist"}
                  >
                    <Star className={`w-3 h-3 ${watchedTickers.has(alert.ticker.toUpperCase()) ? "fill-current" : ""}`} />
                  </button>
                </div>
              </td>
              <td className="px-1 py-0.5 text-gray-700 dark:text-gray-400">
                <FormTypeTooltip formType={alert.form_type}>
                  <span className="cursor-help underline decoration-dotted decoration-gray-500 dark:decoration-gray-500 hover:text-gray-900 dark:hover:text-gray-300 whitespace-nowrap">
                    {alert.form_type}
                  </span>
                </FormTypeTooltip>
              </td>
              <td className="px-1 py-0.5 text-gray-700 dark:text-gray-300 whitespace-nowrap">
                <div className="truncate" title={alert.offering_type || undefined}>
                  {alert.offering_type || "-"}
                </div>
              </td>
              <td className="px-1 py-0.5">
                <span className={`font-semibold ${getRiskColor(alert.risk_score)} whitespace-nowrap`}>
                  {alert.risk_score}
                </span>
              </td>
              <td className="px-1 py-0.5 text-gray-700 dark:text-gray-300">
                <div className="space-y-0">
                  {alert.price_at_filing ? (
                    <div className="text-[10px]">
                      <span className="text-gray-500 dark:text-gray-500">At:</span>{" "}
                      <span className="font-medium">${alert.price_at_filing.toFixed(2)}</span>
                    </div>
                  ) : (
                    <div className="text-[10px] text-gray-400 dark:text-gray-600">-</div>
                  )}
                  {alert.price_7days_later ? (
                    <div className="text-[10px]">
                      <span className="text-gray-500 dark:text-gray-500">+7d:</span>{" "}
                      <span className={`font-medium ${
                        alert.price_at_filing 
                          ? (alert.price_7days_later >= alert.price_at_filing 
                              ? "text-green-600 dark:text-green-400" 
                              : "text-red-600 dark:text-red-400")
                          : ""
                      }`}>
                        ${alert.price_7days_later.toFixed(2)}
                      </span>
                      {alert.price_at_filing && (
                        <span className={`text-[10px] ml-0.5 ${
                          alert.price_7days_later >= alert.price_at_filing
                            ? "text-green-600 dark:text-green-400"
                            : "text-red-600 dark:text-red-400"
                        }`}>
                          ({alert.price_7days_later >= alert.price_at_filing ? "+" : ""}
                          {((alert.price_7days_later - alert.price_at_filing) / alert.price_at_filing * 100).toFixed(1)}%)
                        </span>
                      )}
                    </div>
                  ) : alert.price_at_filing ? (
                    <div className="text-[10px] text-gray-400 dark:text-gray-600">Pending</div>
                  ) : null}
                </div>
              </td>
              <td className="px-1 py-0.5 text-gray-700 dark:text-gray-300 whitespace-nowrap">
                {alert.share_price ? (
                  <span className="text-[10px] font-medium">${parseFloat(alert.share_price.replace(/[$,]/g, "")).toFixed(2)}</span>
                ) : (
                  <span className="text-[10px] text-gray-400 dark:text-gray-600">-</span>
                )}
              </td>
              <td className="px-1 py-0.5 text-gray-700 dark:text-gray-300 whitespace-nowrap">
                {formatCurrency(alert.base_offering_amount || alert.offering_amount)}
              </td>
              <td className="px-1 py-0.5 text-gray-700 dark:text-gray-300 whitespace-nowrap">
                {alert.share_equivalent ? (
                  <span className="font-mono text-[10px]">
                    {parseInt(alert.share_equivalent.replace(/,/g, "")).toLocaleString()}
                  </span>
                ) : (
                  "-"
                )}
              </td>
              <td className="px-1 py-0.5">
                <div className="flex flex-wrap gap-0.5">
                  {alert.toxic_debt_detected && (
                    <span className="text-[10px] px-1 py-0.5 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded font-medium">
                      Toxic Debt
                    </span>
                  )}
                  {alert.management_turnover && (
                    <span className="text-[10px] px-1 py-0.5 bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400 rounded font-medium">
                      Resignation
                    </span>
                  )}
                  {alert.warrants_found && (
                    <span className="text-[10px] px-1 py-0.5 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400 rounded font-medium">
                      Warrants
                    </span>
                  )}
                  {hasValidUnderwriter(alert.underwriter_found) && (
                    <span className="text-[10px] px-1 py-0.5 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400 rounded font-medium">
                      Underwriter
                    </span>
                  )}
                </div>
              </td>
              <td className="px-1 py-0.5">
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    e.preventDefault();
                    console.log('[AlertTable] Details button clicked for alert:', alert.ticker, alert.id);
                    if (onRowClick) {
                      onRowClick(alert);
                    } else {
                      console.warn('[AlertTable] onRowClick is not defined');
                    }
                  }}
                  className="text-blue-400 hover:text-blue-300 inline-flex items-center transition-colors cursor-pointer"
                  title="View details"
                >
                  <ExternalLink className="w-3 h-3" />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
