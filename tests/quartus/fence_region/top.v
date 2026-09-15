// Verilog-2001 design for TC-FENCE-001.
//
// Each module keeps registers that the Fitter cannot optimize away, so both
// hierarchies still occupy resources inside their Logic Lock regions after
// synthesis. The connection from the isolated module to the non-isolated
// module is what forces routing to cross a region boundary.

module isolated_module (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [7:0] data_in,
    output wire [7:0] data_out
);
    (* preserve *) reg [7:0] state;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            state <= 8'h01;
        else
            state <= {state[6:0], state[7] ^ state[5]} ^ data_in;
    end

    assign data_out = state;
endmodule

module non_isolated_module (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [7:0] data_in,
    output wire [7:0] data_out
);
    (* preserve *) reg [7:0] accumulator;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            accumulator <= 8'h00;
        else
            accumulator <= accumulator + data_in;
    end

    assign data_out = accumulator;
endmodule

module top (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [7:0] data_in,
    output wire [7:0] data_out
);
    wire [7:0] isolated_data;
    wire [7:0] non_isolated_data;

    isolated_module u_isolated (
        .clk      (clk),
        .rst_n    (rst_n),
        .data_in  (data_in),
        .data_out (isolated_data)
    );

    non_isolated_module u_non_isolated (
        .clk      (clk),
        .rst_n    (rst_n),
        .data_in  (isolated_data),
        .data_out (non_isolated_data)
    );

    assign data_out = non_isolated_data;
endmodule
