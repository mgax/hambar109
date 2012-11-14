class BubbleChart
  constructor: (data) ->
    @data = data
    @width = 940
    @height = 600

    @tooltip = CustomTooltip("gates_tooltip", 240)

    # locations the nodes will move towards
    # depending on which view is currently being
    # used
    @center = {x: @width / 2, y: @height / 2}
    @year_centers = () =>
      years = {}
      years_list = []
      width = @width
      height = @height
      i = 0
      years_list = (parseInt(d.name) for d in @data.children)
      years_list.sort (a,b) -> a - b
      years_list.forEach (d) ->
        years[d] = {x: width/years_list.length * i + 20, y: height / 6}
        i = i + 1

      years

    # used when setting up force and
    # moving around nodes
    @layout_gravity = -0.01
    @damper = 0.1

    # these will be set in create_nodes and create_vis
    @vis = null
    @nodes = []
    @force = null
    @circles = null

    # nice looking colors - no reason to buck the trend
    @fill_color = d3.scale.ordinal()
      .domain(["low", "medium", "high"])
      .range(["#d84b2a", "#beccae", "#7aa25c"])

    # use the max total_amount in the data as the max in the scale's domain
    max_amount = d3.max(@data.children, (d) -> parseInt(d.size))
    @radius_scale = d3.scale.pow().exponent(0.5).domain([0, max_amount]).range([2, 85])
    @min_radius_scale = d3.scale.pow().exponent(0.5).domain([0, max_amount]).range([2, 20])
    this.create_nodes()
    this.create_vis()

  # create node objects from original data
  # that will serve as the data behind each
  # bubble in the vis, then add each node
  # to @nodes to be used later
  create_nodes: () =>
    @data.children.forEach (d) =>
      node = {
        id: d.name
        radius: @radius_scale(parseInt(d.size))
        min_radius: @min_radius_scale(parseInt(d.size))
        value: d.size
        name: d.name
        org: d.name
        group: d.name
        year: d.name
        x: Math.random() * 900
        y: Math.random() * 800
      }
      @nodes.push node

    @nodes.sort (a,b) -> b.value - a.value


  # create svg at #vis and then 
  # create circle representation for each node
  create_vis: () =>
    if @vis
      debugger
    else
      @vis = d3.select("#vis").append("svg:svg")
        .attr("width", @width)
        .attr("height", @height)
        .attr("id", "svg_vis")

    @circles = @vis.selectAll("circle")
      .data(@nodes, (d) -> d.id)

    # used because we need 'this' in the 
    # mouse callbacks
    that = this

    # radius will be set to 0 initially.
    # see transition below
    @circles.enter().append("svg:circle")
      .attr("r", 0)
      .attr("fill", (d) => @fill_color(d.group))
      .attr("stroke-width", 2)
      .attr("stroke", (d) => d3.rgb(@fill_color(d.group)).darker())
      .attr("id", (d) -> "bubble_#{d.id}")
      .on("mouseover", (d,i) -> that.show_details(d,i,this))
      .on("mouseout", (d,i) -> that.hide_details(d,i,this))

    # Fancy transition to make bubbles appear, ending with the
    # correct radius
    #@circles.transition().duration(2000).attr("r", (d) -> d.radius)


  # Charge function that is called for each node.
  # Charge is proportional to the diameter of the
  # circle (which is stored in the radius attribute
  # of the circle's associated data.
  # This is done to allow for accurate collision 
  # detection with nodes of different sizes.
  # Charge is negative because we want nodes to 
  # repel.
  # Dividing by 8 scales down the charge to be
  # appropriate for the visualization dimensions.
  charge: (d) ->
    -Math.pow(d.radius, 2.0) / 8

  # Starts up the force layout with
  # the default values
  start: () =>
    @force = d3.layout.force()
      .nodes(@nodes)
      .size([@width, @height])

  # Sets up force layout to display
  # all nodes in one circle.
  display_group_all: () =>
    @force.gravity(@layout_gravity)
      .charge(this.charge)
      .friction(0.9)
      .on "tick", (e) =>
        @circles.each(this.move_towards_center(e.alpha))
          .attr("cx", (d) -> d.x)
          .attr("cy", (d) -> d.y)
          .attr("r", (d) -> d.radius)
    @force.start()

    this.hide_years()

  # Moves all circles towards the @center
  # of the visualization
  move_towards_center: (alpha) =>
    (d) =>
      d.x = d.x + (@center.x - d.x) * (@damper + 0.02) * alpha
      d.y = d.y + (@center.y - d.y) * (@damper + 0.02) * alpha

  # sets the display of bubbles to be separated
  # into each year. Does this by calling move_towards_year
  display_by_year: () =>
    @force.gravity(@layout_gravity)
      .charge(this.charge)
      .friction(0.9)
      .on "tick", (e) =>
        @circles.each(this.move_towards_year(e.alpha))
          .attr("cx", (d) -> d.x)
          .attr("cy", (d) -> d.y)
          .attr("r", (d) -> d.radius)
    @force.start()

    this.display_years()

  # move all circles to their associated @year_centers 
  move_towards_year: (alpha) =>
    (d) =>
      target = @year_centers()[d.year]
      d.radius = if d.radius > d.min_radius then d.radius/2 * 1.85 else d.min_radius
      d.x = d.x + (target.x - d.x) * (@damper + 0.02)# * alpha * 1.1
      d.y = d.y + (target.y - d.y) * (@damper + 0.02)# * alpha * 1.1


  # Method to display year titles
  display_years: () =>
    years_x = {}
    i = 0
    width = @width
    years_list = (parseInt(d.name) for d in @data.children)
    years_list.sort (a,b) -> a - b
    years_list.forEach (d) ->
      years_x[d] = width/years_list.length * i + 20
      i = i+1
    years_data = d3.keys(years_x)
    years = @vis.selectAll(".years")
      .data(years_data)

    years.enter().append("svg:text")
      .attr("class", "years")
      .attr("x", (d) => years_x[d] )
      .attr("y", @height/6 - 30)
      .attr("text-anchor", "middle") .text((d) -> d)

  # Method to hide year titiles
  hide_years: () =>
    years = @vis.selectAll(".years").remove()

  show_details: (data, i, element) =>
    d3.select(element).attr("stroke", "black")
    content ="<span class=\"name\">Year:</span><span class=\"value\"> #{data.year}</span><br/>"
    content +="<span class=\"name\">Files:</span><span class=\"value\"> #{data.value} </span>"
    @tooltip.showTooltip(content,d3.event)


  hide_details: (data, i, element) =>
    d3.select(element).attr("stroke", (d) => d3.rgb(@fill_color(d.group)).darker())
    @tooltip.hideTooltip()


root = exports ? this

$ ->
  chart = null

  render_vis = (csv) ->
    chart = new BubbleChart csv
    chart.start()
    root.display_all()
  root.display_all = () =>
    chart.display_group_all()
  root.display_year = () =>
    chart.display_by_year()
  root.toggle_view = (view_type) =>
    if view_type == 'year'
      root.display_year()
    else
      root.display_all()

  d3.json "/stats_json", render_vis
