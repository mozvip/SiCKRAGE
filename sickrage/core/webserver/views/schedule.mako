<%inherit file="./layouts/main.mako"/>
<%!
    import re
    import time
    import datetime

    import sickrage
    from sickrage.core.helpers import anon_url, srdatetime
    from sickrage.core.media.util import showImage
    from sickrage.indexers import srIndexerApi
%>
<%block name="content">
    <%namespace file="./includes/quality_defaults.mako" import="renderQualityPill"/>
    <div class="row">
        <div class="col-md-12 text-center">
            % if layout == 'list':
                <label for="popover" class="badge" style="background-color: #333333;">Select Columns:
                    <button id="popover" type="button" class="form-control form-control-inline input-sm"><b
                            class="caret"></b></button>
                </label>
            % else:
                <label for="sortby" class="badge" style="background-color: #333333;">Sort By:
                    <select id="sortby" name="sort" class="form-control form-control-inline input-sm"
                            onchange="location = this.options[this.selectedIndex].value;">
                        <option value="${srWebRoot}/setScheduleSort/?sort=date" ${('', 'selected')[sickrage.srCore.srConfig.COMING_EPS_SORT == 'date']} >
                            Date
                        </option>
                        <option value="${srWebRoot}/setScheduleSort/?sort=network" ${('', 'selected')[sickrage.srCore.srConfig.COMING_EPS_SORT == 'network']} >
                            Network
                        </option>
                        <option value="${srWebRoot}/setScheduleSort/?sort=show" ${('', 'selected')[sickrage.srCore.srConfig.COMING_EPS_SORT == 'show']} >
                            Show
                        </option>
                    </select>
                </label>
            % endif

            <label for="viewpaused" class="badge" style="background-color: #333333;">View Paused:
                <select id="viewpaused" name="viewpaused" class="form-control form-control-inline input-sm"
                        onchange="location = this.options[this.selectedIndex].value;">
                    <option value="${srWebRoot}/toggleScheduleDisplayPaused" ${('', 'selected')[not bool(sickrage.srCore.srConfig.COMING_EPS_DISPLAY_PAUSED)]}>
                        Hidden
                    </option>
                    <option value="${srWebRoot}/toggleScheduleDisplayPaused" ${('', 'selected')[bool(sickrage.srCore.srConfig.COMING_EPS_DISPLAY_PAUSED)]}>
                        Shown
                    </option>
                </select>
            </label>

            <label for="layout" class="badge" style="background-color: #333333;">Layout:
                <select id="layout" name="layout" class="form-control form-control-inline input-sm"
                        onchange="location = this.options[this.selectedIndex].value;">
                    <option value="${srWebRoot}/setScheduleLayout/?layout=poster" ${('', 'selected')[sickrage.srCore.srConfig.COMING_EPS_LAYOUT == 'poster']} >
                        Poster
                    </option>
                    <option value="${srWebRoot}/setScheduleLayout/?layout=calendar" ${('', 'selected')[sickrage.srCore.srConfig.COMING_EPS_LAYOUT == 'calendar']} >
                        Calendar
                    </option>
                    <option value="${srWebRoot}/setScheduleLayout/?layout=banner" ${('', 'selected')[sickrage.srCore.srConfig.COMING_EPS_LAYOUT == 'banner']} >
                        Banner
                    </option>
                    <option value="${srWebRoot}/setScheduleLayout/?layout=list" ${('', 'selected')[sickrage.srCore.srConfig.COMING_EPS_LAYOUT == 'list']} >
                        List
                    </option>
                </select>
            </label>

            <div class="key">
                % if 'calendar' != layout:
                    <b>Key:</b>
                    <span class="listing-key listing-overdue">Missed</span>
                    <span class="listing-key listing-current">Today</span>
                    <span class="listing-key listing-default">Soon</span>
                    <span class="listing-key listing-toofar">Later</span>
                % endif
                <a class="btn btn-inline forceBacklog" href="webcal://${srHost}:${srHttpPort}/calendar">
                    <i class="icon-calendar icon-white"></i>Subscribe</a>
            </div>
        </div>
    </div>
    <div class="row">
        % if 'list' == layout:
            <div class="col-md-12">
                <% show_div = 'listing-default' %>

                <table id="showListTable" class="sickrageTable tablesorter seasonstyle" cellspacing="1" border="0"
                       cellpadding="0">

                    <thead>
                    <tr>
                        <th>Airdate (${('local', 'network')[sickrage.srCore.srConfig.TIMEZONE_DISPLAY == 'network']})
                        </th>
                        <th>Ends</th>
                        <th>Show</th>
                        <th>Next Ep</th>
                        <th>Next Ep Name</th>
                        <th>Network</th>
                        <th>Run time</th>
                        <th>Quality</th>
                        <th>Indexers</th>
                        <th>Search</th>
                    </tr>
                    </thead>

                    <tbody style="text-shadow:none;">
                        % for cur_result in results:
                            % if not int(cur_result['paused']) or sickrage.srCore.srConfig.COMING_EPS_DISPLAY_PAUSED:
                                <%
                                    cur_indexer = int(cur_result['indexer'])
                                    run_time = int(cur_result['runtime'])

                                    cur_ep_airdate = cur_result['localtime'].date()
                                    cur_ep_enddate = cur_result['localtime']

                                    if run_time:
                                        cur_ep_enddate += datetime.timedelta(minutes = run_time)

                                    if cur_ep_enddate < today:
                                        show_div = 'listing-overdue'
                                    elif cur_ep_airdate >= next_week.date():
                                        show_div = 'listing-toofar'
                                    elif today.date() <= cur_ep_airdate < next_week.date():
                                        if cur_ep_airdate == today.date():
                                            show_div = 'listing-current'
                                        else:
                                            show_div = 'listing-default'
                                %>

                                <tr class="${show_div}">
                                    <td align="center" nowrap="nowrap">
                                        <% airDate = srdatetime.srDateTime.convert_to_setting(cur_result['localtime']) %>
                                        <time datetime="${airDate.isoformat()}"
                                              class="date">${srdatetime.srDateTime.srfdatetime(airDate)}</time>
                                    </td>

                                    <td align="center" nowrap="nowrap">
                                        <% ends = srdatetime.srDateTime.convert_to_setting(cur_ep_enddate) %>
                                        <time datetime="${ends.isoformat()}"
                                              class="date">${srdatetime.srDateTime.srfdatetime(ends)}</time>
                                    </td>

                                    <td class="tvShow" nowrap="nowrap"><a
                                            href="${srWebRoot}/home/displayShow?show=${cur_result['showid']}">${cur_result['show_name']}</a>
                                        % if int(cur_result['paused']):
                                            <span class="pause">[paused]</span>
                                        % endif
                                    </td>

                                    <td nowrap="nowrap" align="center">
                                        ${'S{:02d}E{:02d}'.format(int(cur_result['season']), int(cur_result['episode']))}
                                    </td>

                                    <td>
                                        % if cur_result['description']:
                                            <img alt="" src="${srWebRoot}/images/info32.png" height="16" width="16"
                                                 class="plotInfo"
                                                 title="${cur_result["description"]}"
                                                 id="plot_info_${'{}_{}_{}'.format(cur_result['showid'], cur_result['season'], cur_result['episode'])}"/>
                                        % else:
                                            <img alt="" src="${srWebRoot}/images/info32.png" width="16" height="16"
                                                 title=""
                                                 class="plotInfoNone"/>
                                        % endif
                                        ${cur_result['name']}
                                    </td>

                                    <td align="center">
                                        ${cur_result['network']}
                                    </td>

                                    <td align="center">
                                        ${run_time}min
                                    </td>

                                    <td align="center">
                                        ${renderQualityPill(cur_result['quality'], showTitle=True)}
                                    </td>

                                    <td align="center" style="vertical-align: middle;">
                                        % if cur_result['imdb_id']:
                                            <a href="${anon_url('http://www.imdb.com/title/', cur_result['imdb_id'])}"
                                               rel="noreferrer" onclick="window.open(this.href, '_blank'); return false"
                                               title="http://www.imdb.com/title/${cur_result['imdb_id']}"><img
                                                    alt="[imdb]"
                                                    height="16"
                                                    width="16"
                                                    src="${srWebRoot}/images/imdb.png"/></a>
                                        % endif
                                        <a href="${anon_url(srIndexerApi(cur_indexer).config['show_url'], cur_result['showid'])}"
                                           rel="noreferrer" onclick="window.open(this.href, '_blank'); return false"
                                           title="${srIndexerApi(cur_indexer).config['show_url']}${cur_result['showid']}">
                                            <img alt="${srIndexerApi(cur_indexer).name}" height="16" width="16"
                                                 src="${srWebRoot}/images/${srIndexerApi(cur_indexer).config['icon']}"/>
                                        </a>
                                    </td>

                                    <td align="center">
                                        <a href="${srWebRoot}/home/searchEpisode?show=${cur_result['showid']}&season=${cur_result['season']}&episode=${cur_result['episode']}"
                                           title="${_('Manual Search')}"
                                           id="forceUpdate-${cur_result['showid']}x${cur_result['season']}x${cur_result['episode']}"
                                           class="forceUpdate epSearch">
                                            <img alt="[search]" height="16" width="16"
                                                 src="${srWebRoot}/images/search16.png"
                                                 id="forceUpdateImage-${cur_result['showid']}"/>
                                        </a>
                                    </td>
                                </tr>
                            % endif
                        % endfor
                    </tbody>

                    <tfoot>
                    <tr>
                        <th rowspan="1" colspan="10" align="center">&nbsp</th>
                    </tr>
                    </tfoot>
                </table>
            </div>
        % elif layout in ['banner', 'poster']:
            <div class="col-lg-10 col-lg-offset-1 col-md-10 col-md-offset-1 col-sm-12 col-xs-12">
                <!-- start non list view //-->
                <%
                    cur_segment = None
                    too_late_header = False
                    missed_header = False
                    today_header = False
                    show_div = 'ep_listing listing-default'
                %>
                % if sickrage.srCore.srConfig.COMING_EPS_SORT == 'show':
                    <br/><br/>
                % endif

                % for cur_result in results:
                    % if not int(cur_result['paused']) or sickrage.srCore.srConfig.COMING_EPS_DISPLAY_PAUSED:
                    <%
                        cur_indexer = int(cur_result['indexer'])

                        run_time = int(cur_result['runtime'])
                        cur_ep_airdate = cur_result['localtime'].date()

                        if run_time:
                            cur_ep_enddate = cur_result['localtime'] + datetime.timedelta(minutes = run_time)
                        else:
                            cur_ep_enddate = cur_result['localtime']
                    %>

                    % if sickrage.srCore.srConfig.COMING_EPS_SORT == 'network':
                        <% show_network = ('no network', cur_result['network'])[bool(cur_result['network'])] %>
                        % if cur_segment != show_network:
                            <div>
                                <br/>
                                <h2 class="network">${show_network}</h2>
                            </div>

                        <% cur_segment = cur_result['network'] %>
                        % endif

                        % if cur_ep_enddate < today:
                            <% show_div = 'ep_listing listing-overdue' %>
                        % elif cur_ep_airdate >= next_week.date():
                            <% show_div = 'ep_listing listing-toofar' %>
                        % elif cur_ep_enddate >= today and cur_ep_airdate < next_week.date():
                            % if cur_ep_airdate == today.date():
                                <% show_div = 'ep_listing listing-current' %>
                            % else:
                                <% show_div = 'ep_listing listing-default' %>
                            % endif
                        % endif

                    % elif sickrage.srCore.srConfig.COMING_EPS_SORT == 'date':
                        % if cur_segment != cur_ep_airdate:
                            % if cur_ep_enddate < today and cur_ep_airdate != today.date() and not missed_header:
                                <br/>
                                <h2 class="day">Missed</h2>
                            <% missed_header = True %>
                            % elif cur_ep_airdate >= next_week.date() and not too_late_header:
                                <br/>
                                <h2 class="day">Later</h2>
                            <% too_late_header = True %>
                            % elif cur_ep_enddate >= today and cur_ep_airdate < next_week.date():
                                % if cur_ep_airdate == today.date():
                                    <br/>
                                    <h2 class="day">${datetime.date.fromordinal(cur_ep_airdate.toordinal()).strftime('%A').decode(sickrage.srCore.SYS_ENCODING).capitalize()}
                                        <span style="font-size: 14px; vertical-align: top;">[Today]</span>
                                    </h2>
                                <% today_header = True %>
                                % else:
                                    <br/>
                                    <h2 class="day">${datetime.date.fromordinal(cur_ep_airdate.toordinal()).strftime('%A').decode(sickrage.srCore.SYS_ENCODING).capitalize()}</h2>
                                % endif
                            % endif
                            <% cur_segment = cur_ep_airdate %>
                        % endif

                        % if cur_ep_airdate == today.date() and not today_header:
                            <div>
                                <br/>
                                <h2 class="day">${datetime.date.fromordinal(cur_ep_airdate.toordinal()).strftime('%A').decode(sickrage.srCore.SYS_ENCODING).capitalize()}
                                    <span style="font-size: 14px; vertical-align: top;">[Today]</span>
                                </h2>
                            </div>
                        <% today_header = True %>
                        % endif

                        % if cur_ep_enddate < today:
                            <% show_div = 'ep_listing listing-overdue' %>
                        % elif cur_ep_airdate >= next_week.date():
                            <% show_div = 'ep_listing listing-toofar' %>
                        % elif cur_ep_enddate >= today and cur_ep_airdate < next_week.date():
                            % if cur_ep_airdate == today.date():
                                <% show_div = 'ep_listing listing-current' %>
                            % else:
                                <% show_div = 'ep_listing listing-default'%>
                            % endif
                        % endif

                    % elif sickrage.srCore.srConfig.COMING_EPS_SORT == 'show':
                        % if cur_ep_enddate < today:
                            <% show_div = 'ep_listing listing-overdue listingradius' %>
                        % elif cur_ep_airdate >= next_week.date():
                            <% show_div = 'ep_listing listing-toofar listingradius' %>
                        % elif cur_ep_enddate >= today and cur_ep_airdate < next_week.date():
                            % if cur_ep_airdate == today.date():
                                <% show_div = 'ep_listing listing-current listingradius' %>
                            % else:
                                <% show_div = 'ep_listing listing-default listingradius' %>
                            % endif
                        % endif
                    % endif

                        <div class="${show_div}" id="listing-${cur_result['showid']}">
                            <div class="tvshowDiv">
                                <table width="100%" border="0" cellpadding="0" cellspacing="0">
                                <tr>
                                    <th ${('class="nobg"', 'rowspan="3"')['poster' == layout]} valign="top">
                                        <a href="${srWebRoot}/home/displayShow?show=${cur_result['showid']}">
                                            <img alt="" class="${('posterThumb', 'bannerThumb')[layout == 'banner']}"
                                                 src="${srWebRoot}${srWebRoot}${showImage(cur_result['showid'], (layout, 'poster_thumb')[layout == 'poster']).url}"/>
                                        </a>
                                    </th>
                                    % if 'banner' == layout:
                                        </tr>
                                        <tr>
                                    % endif
                                    <td class="next_episode">
                                        <div class="clearfix">
                                <span class="tvshowTitle">
                                    <a href="${srWebRoot}/home/displayShow?show=${cur_result['showid']}">${cur_result['show_name']}
                                        ${('', '<span class="pause">[paused]</span>')[int(cur_result['paused'])]}
                                    </a>
                                </span>

                                            <span class="tvshowTitleIcons">
                                    % if cur_result['imdb_id']:
                                        <a href="${anon_url('http://www.imdb.com/title/', cur_result['imdb_id'])}"
                                           rel="noreferrer"
                                           onclick="window.open(this.href, '_blank'); return false"
                                           title="http://www.imdb.com/title/${cur_result['imdb_id']}"><img alt="[imdb]"
                                                                                                           height="16"
                                                                                                           width="16"
                                                                                                           src="${srWebRoot}/images/imdb.png"/></a>
                                    % endif
                                                <a href="${anon_url(srIndexerApi(cur_indexer).config['show_url'], cur_result['showid'])}"
                                                   rel="noreferrer"
                                                   onclick="window.open(this.href, '_blank'); return false"
                                                   title="${srIndexerApi(cur_indexer).config['show_url']}"><img
                                                        alt="${srIndexerApi(cur_indexer).name}" height="16" width="16"
                                                        src="${srWebRoot}/images/${srIndexerApi(cur_indexer).config['icon']}"/></a>
                                    <span><a
                                            href="${srWebRoot}/home/searchEpisode?show=${cur_result['showid']}&season=${cur_result['season']}&episode=${cur_result['episode']}"
                                            title="Manual Search" id="forceUpdate-${cur_result['showid']}"
                                            class="epSearch forceUpdate"><img alt="[search]" height="16" width="16"
                                                                              src="${srWebRoot}/images/search16.png"
                                                                              id="forceUpdateImage-${cur_result['showid']}"/></a></span>
                                </span>
                                        </div>

                                        <span class="title">Next Episode:</span>
                                        <span>${'S{:02d}E{:02d}'.format(int(cur_result['season']), int(cur_result['episode']))}
                                            - ${cur_result['name']}</span>

                                        <div class="clearfix">
                                            <span class="title">Airs: </span><span
                                                class="airdate">${srdatetime.srDateTime.srfdatetime(cur_result['localtime'])}</span>${('', '<span> on %s</span>' % cur_result['network'])[bool(cur_result['network'])]}
                                        </div>

                                        <div class="clearfix">
                                            <span class="title">Quality:</span>
                                            ${renderQualityPill(cur_result['quality'], showTitle=True)}
                                        </div>
                                    </td>
                                </tr>
                                    <tr>
                                        <td style="vertical-align: top;">
                                            <div>
                                                % if cur_result['description']:
                                                    <span class="title" style="vertical-align:middle;">Plot:</span>
                                                    <img class="ep_summaryTrigger" src="${srWebRoot}/images/plus.png"
                                                         height="16" width="16" alt=""
                                                         title="${_('Toggle Summary')}"/>
                                                    <div class="ep_summary">${cur_result['description']}</div>
                                                % else:
                                                    <span class="title ep_summaryTriggerNone"
                                                          style="vertical-align:middle;">Plot:</span>
                                                    <img class="ep_summaryTriggerNone"
                                                         src="${srWebRoot}/images/plus.png"
                                                         height="16" width="16"
                                                         alt=""/>
                                                % endif
                                            </div>
                                        </td>
                                    </tr>
                                </table>
                            </div>
                        </div>

                        <!-- end ${cur_result['show_name']} //-->
                    % endif
                % endfor
            </div>
        % elif 'calendar' == layout:
            <div class="col-md-12">
                <% dates = [today.date() + datetime.timedelta(days = i) for i in range(7)] %>
                <% tbl_day = 0 %>
                <br/>
                <br/>
                <div class="calendarWrapper">

                    % for day in dates:
                    <% tbl_day += 1 %>
                        <table class="sickrageTable tablesorter calendarTable ${'cal-{}'.format(('even', 'odd')[bool(tbl_day % 2)])}"
                               cellspacing="0" border="0" cellpadding="0">
                            <thead>
                            <tr>
                                <th>${day.strftime('%A').decode(sickrage.srCore.SYS_ENCODING).capitalize()}</th>
                            </tr>
                            </thead>
                            <tbody>
                                <% day_has_show = False %>
                                % for cur_result in results:
                                    % if not int(cur_result['paused']) or sickrage.srCore.srConfig.COMING_EPS_DISPLAY_PAUSED:

                                        <% cur_indexer = int(cur_result['indexer']) %>
                                        <% run_time = int(cur_result['runtime']) %>
                                        <% airday = cur_result['localtime'].date() %>

                                        % if airday == day:
                                            % try:
                                            <% day_has_show = True %>
                                            <% airtime = srdatetime.srDateTime.fromtimestamp(time.mktime(cur_result['localtime'].timetuple())).srftime().decode(sickrage.srCore.SYS_ENCODING) %>
                                            % if sickrage.srCore.srConfig.TRIM_ZERO:
                                                <% airtime = re.sub(r'0(\d:\d\d)', r'\1', airtime, 0, re.IGNORECASE | re.MULTILINE) %>
                                            % endif
                                            % except OverflowError:
                                            <% airtime = "Invalid" %>
                                            % endtry

                                            <tr>
                                                <td class="calendarShow">
                                                    <div class="poster">
                                                        <a title="${cur_result['show_name']}"
                                                           href="${srWebRoot}/home/displayShow?show=${cur_result['showid']}"><img
                                                                alt=""
                                                                src="${srWebRoot}${srWebRoot}${showImage(cur_result['showid'], 'poster_thumb').url}"/></a>
                                                    </div>
                                                    <div class="text">
                                                <span class="airtime">
                                                    ${airtime} on ${cur_result["network"]}
                                                </span>
                                                        <span class="episode-title" title="${cur_result['name']}">
                                                    ${'S{:02d}E{:02d}'.format(int(cur_result['season']), int(cur_result['episode']))}
                                                            - ${cur_result['name']}
                                                </span>
                                                    </div>
                                                </td> <!-- end ${cur_result['show_name']} -->
                                            </tr>
                                        % endif

                                    % endif
                                % endfor
                                % if not day_has_show:
                                    <tr>
                                        <td class="calendarShow"><span class="show-status">No shows for this day</span>
                                        </td>
                                    </tr>
                                % endif
                            </tbody>
                        </table>
                    % endfor
                </div>
            </div>
        % endif
    </div>
</%block>