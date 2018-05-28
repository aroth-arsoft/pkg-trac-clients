# -*- coding: utf-8 -*-

# IF YOU ADD A NEW SECTION OF REPORTS, You will need to make
# sure that section is also added to the reports hashtable
# near the bottom

# Please try to keep this clean

billing_reports = [{
    'uuid': 'cd175fb0-0c74-48e4-816f-d72b4ba98fc1',
    'title': 'Client Work Summary',
    'description': '',
    'version': 1,
    'sql': """
SELECT
  __group__, __style__,  ticket, summary, newvalue AS Work_added,
  time, _ord
FROM(
  SELECT '' AS __style__, t.id AS ticket,
    SUM(CAST(newvalue AS DECIMAL)) AS newvalue, t.summary AS summary,
    MAX(ticket_change.time) AS time, client.value AS __group__, 0 AS _ord
  FROM ticket_change
  JOIN ticket t ON t.id = ticket_change.ticket
  LEFT JOIN ticket_custom AS billable ON billable.ticket = t.id
    AND billable.name = 'billable'
  LEFT JOIN ticket_custom AS client ON client.ticket = t.id
    AND client.name = 'client'
  WHERE field = 'hours' AND
    t.status IN ($NEW, $ASSIGNED, $REOPENED, $CLOSED)
      AND billable.value IN ($BILLABLE, $UNBILLABLE)
      AND ticket_change.time >= $STARTDATE
      AND ticket_change.time < $ENDDATE
  GROUP BY client.value, t.id, t.summary

  UNION

  SELECT 'background-color:#DFE;' AS __style__, NULL AS ticket,
    sum(CAST(newvalue AS DECIMAL)) AS newvalue, 'Total work done' AS summary,
    NULL AS time, client.value AS __group__, 1 AS _ord
  FROM ticket_change
  JOIN ticket t ON t.id = ticket_change.ticket
  LEFT JOIN ticket_custom AS billable ON billable.ticket = t.id
    AND billable.name = 'billable'
  LEFT JOIN ticket_custom AS client ON client.ticket = t.id
    AND client.name = 'client'
  WHERE field = 'hours' AND
    t.status IN ($NEW, $ASSIGNED, $REOPENED, $CLOSED)
      AND billable.value IN ($BILLABLE, $UNBILLABLE)
      AND ticket_change.time >= $STARTDATE
      AND ticket_change.time < $ENDDATE
  GROUP BY client.value
)  AS tbl
ORDER BY __group__,  _ord ASC, ticket, time
    """
}]

ticket_hours_reports = [{
    'uuid': 'e2ab8124-9309-4d1c-9cec-f8c7b11bf579',
    'title': 'Ticket Hours Grouped By Client',
    'description': '',
    'version': 1,
    'sql': """
SELECT __color__, __group__, __style__, ticket, summary, __component__ ,version,
  severity, milestone, status, owner, estimate_work, total_work, billable,
  _ord

FROM (
SELECT p.value AS __color__,
       client.value AS __group__,
       '' AS __style__,
       t.id AS ticket, summary AS summary,             -- ## Break line here
       component AS __component__,version, severity, milestone, status, owner,
       CAST(estimatedhours.value AS DECIMAL) AS estimate_work,
       CAST(totalhours.value AS DECIMAL) AS Total_work,
       CASE WHEN billable.value = 1 THEN 'Y'
            ELSE 'N'
       END AS billable,
       time AS created, changetime AS modified,         -- ## Dates are formatted
       description AS _description_,                    -- ## Uses a full row
       changetime AS _changetime,
       reporter AS _reporter
       ,0 AS _ord

  FROM ticket AS t
  JOIN enum AS p ON p.name=t.priority AND p.type='priority'

LEFT JOIN ticket_custom AS estimatedhours ON estimatedhours.name='estimatedhours'
      AND estimatedhours.ticket = t.id
LEFT JOIN ticket_custom AS totalhours ON totalhours.name='totalhours'
      AND totalhours.ticket = t.id
LEFT JOIN ticket_custom AS billable ON billable.name='billable'
      AND billable.ticket = t.id
LEFT JOIN ticket_custom AS client ON client.name='client'
      AND client.ticket = t.id

  WHERE t.status IN ($NEW, $ASSIGNED, $REOPENED, $CLOSED)
    AND billable.value IN ($BILLABLE, $UNBILLABLE)


UNION

SELECT '1' AS __color__,
       client.value AS __group__,
       'background-color:#DFE;' AS __style__,
       NULL AS ticket, 'Total work' AS summary,
       t.component AS __component__, NULL AS version, NULL AS severity,
       NULL AS  milestone, NULL AS status,
       NULL AS owner,
       SUM(CAST(estimatedhours.value AS DECIMAL)) AS estimate_work,
       SUM(CAST(totalhours.value AS DECIMAL)) AS Total_work,
       NULL AS billable,
       NULL AS created,
       NULL AS modified,         -- ## Dates are formatted

       NULL AS _description_,
       NULL AS _changetime,
       NULL AS _reporter
       ,1 AS _ord
  FROM ticket AS t
  JOIN enum AS p ON p.name=t.priority AND p.type='priority'

LEFT JOIN ticket_custom AS estimatedhours ON estimatedhours.name='estimatedhours'
      AND estimatedhours.ticket = t.id

LEFT JOIN ticket_custom AS totalhours ON totalhours.name='totalhours'
      AND totalhours.ticket = t.id

LEFT JOIN ticket_custom AS billable ON billable.name='billable'
      AND billable.ticket = t.id

LEFT JOIN ticket_custom AS client ON client.name='client'
      AND client.ticket = t.id

  WHERE t.status IN ($NEW, $ASSIGNED, $REOPENED, $CLOSED)
    AND billable.value IN ($BILLABLE, $UNBILLABLE)
  GROUP BY client.value
)  AS tbl
ORDER BY __group__, _ord ASC,ticket
    """
}, {
    'uuid': '9194d297-bd5a-4225-a28c-e981525b20e1',
    'title': 'Ticket Hours Grouped By Client with Description',
    'description': '',
    'version': 1,
    'sql': """
SELECT __color__, __group__, __style__, ticket, summary, __component__ ,version,
  severity, milestone, status, owner, estimate_work, total_work, billable,
  _description_, _ord

FROM (
SELECT p.value AS __color__,
       client.value AS __group__,
       '' AS __style__,
       t.id AS ticket, summary AS summary,             -- ## Break line here
       component AS __component__,version, severity, milestone, status, owner,
       CAST(estimatedhours.value AS DECIMAL) AS estimate_work,
       CAST(totalhours.value AS DECIMAL) AS Total_work,
       CASE WHEN billable.value = 1 THEN 'Y'
            ELSE 'N'
       END AS billable,
       time AS created, changetime AS modified,         -- ## Dates are formatted
       description AS _description_,                    -- ## Uses a full row
       changetime AS _changetime,
       reporter AS _reporter
       ,0 AS _ord

  FROM ticket AS t
  JOIN enum AS p ON p.name=t.priority AND p.type='priority'

LEFT JOIN ticket_custom AS estimatedhours ON estimatedhours.name='estimatedhours'
      AND estimatedhours.ticket = t.id
LEFT JOIN ticket_custom AS totalhours ON totalhours.name='totalhours'
      AND totalhours.ticket = t.id
LEFT JOIN ticket_custom AS billable ON billable.name='billable'
      AND billable.ticket = t.id
LEFT JOIN ticket_custom AS client ON client.name='client'
      AND client.ticket = t.id

  WHERE t.status IN ($NEW, $ASSIGNED, $REOPENED, $CLOSED)
    AND billable.value IN ($BILLABLE, $UNBILLABLE)


UNION

SELECT '1' AS __color__,
       client.value AS __group__,
       'background-color:#DFE;' AS __style__,
       NULL AS ticket, 'Total work' AS summary,
       t.component AS __component__, NULL AS version, NULL AS severity,
       NULL AS  milestone, NULL AS status,
       NULL AS owner,
       SUM(CAST(estimatedhours.value AS DECIMAL)) AS estimate_work,
       SUM(CAST(totalhours.value AS DECIMAL)) AS Total_work,
       NULL AS billable,
       NULL AS created,
       NULL AS modified,         -- ## Dates are formatted

       NULL AS _description_,
       NULL AS _changetime,
       NULL AS _reporter
       ,1 AS _ord
  FROM ticket AS t
  JOIN enum AS p ON p.name=t.priority AND p.type='priority'

LEFT JOIN ticket_custom AS estimatedhours ON estimatedhours.name='estimatedhours'
      AND estimatedhours.ticket = t.id

LEFT JOIN ticket_custom AS totalhours ON totalhours.name='totalhours'
      AND totalhours.ticket = t.id

LEFT JOIN ticket_custom AS billable ON billable.name='billable'
      AND billable.ticket = t.id

LEFT JOIN ticket_custom AS client ON client.name='client'
      AND client.ticket = t.id

  WHERE t.status IN ($NEW, $ASSIGNED, $REOPENED, $CLOSED)
    AND billable.value IN ($BILLABLE, $UNBILLABLE)
  GROUP BY client.value
)  AS tbl
ORDER BY __group__, _ord ASC,ticket
    """
}]

reports = [{
    'title': 'Billing Reports',
    'reports': billing_reports
}, {
    'title': 'Ticket/Hour Reports',
    'reports': ticket_hours_reports
}]
