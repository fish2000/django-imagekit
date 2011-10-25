#ifndef adderror
    /* #define adderror( b, e ) ( ((b + e) <= 0x00) ? 0x00 : ( (( b + e) >= 0xFF) ? 0xFF : (b + e) ) ) */
    #define adderror( b, e ) ( ((b) < -(e)) ? 0x00 : ( ((0xFF - (b)) < (e)) ? 0xFF : (b + e) ) )
#endif

#ifndef c_min
    #define c_min(a,b) (((a) < (b)) ? (a) : (b))
#endif

unsigned char threshold_matrix[256];
